from rest_framework import serializers
from django.db import transaction

from address.serializers import AddressSerializer
from payments.models import Payment
from delivery.services import reserve_delivery_slot
from delivery.models import DeliveryPerson, DeliverySchedule
from delivery.serializers import DeliveryPersonSerializer
from .models import Order, OrderItem, OrderStatus


class AssignDeliverySerializer(serializers.Serializer):
    delivery_person = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryPerson.objects.all(),
        required=True
    )
    delivery_schedule = serializers.PrimaryKeyRelatedField(
        queryset=DeliverySchedule.objects.all(),
        required=True
    )

    def validate_delivery_person(self, value):
        if not value.can_receive_orders:
            raise serializers.ValidationError(
                'Delivery person must be active and have a completed profile.'
            )
        return value

    def validate_delivery_schedule(self, value):
        if not value.is_available:
            raise serializers.ValidationError(
                'Delivery schedule is not available. It might be full, inactive, or blocked.'
            )
        return value

    def validate(self, attrs):
        order = self.context.get('order')
        if not order:
            # This should not happen if the view provides the context
            raise serializers.ValidationError("Order context is missing.")

        schedule = attrs.get('delivery_schedule')
        if order.delivery_date != schedule.delivery_date:
            raise serializers.ValidationError({
                'delivery_schedule': f"Schedule date ({schedule.delivery_date}) does not match order delivery date ({order.delivery_date})."
            })
        # Check if the order is already assigned
        if order.delivery_person and order.delivery_schedule:
            raise serializers.ValidationError("This order has already been assigned for delivery.")

        return attrs

class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product_variant', 'quantity']


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)
    delivery_slot_id = serializers.IntegerField(write_only=True)
    delivery_date = serializers.DateField(write_only=True)

    class Meta:
        model = Order
        fields = ['items', 'delivery_slot_id', 'delivery_date']

    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data.pop('items')
        delivery_slot_id = validated_data.pop('delivery_slot_id')
        delivery_date = validated_data.pop('delivery_date')

        status = OrderStatus.objects.get(name="Pending")
        with transaction.atomic():
            schedule, delivery_snapshot = reserve_delivery_slot(delivery_slot_id, delivery_date)
            order = Order.objects.create(user=user, status=status, **delivery_snapshot, **validated_data)

            for item_data in items_data:
                OrderItem.objects.create(order=order, **item_data)

        return order


class OrderItemSerializer(serializers.ModelSerializer):
    product_variant_id = serializers.IntegerField(source='product_variant.id', read_only=True)
    product_variant = serializers.StringRelatedField()
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discounted_price = serializers.DecimalField(source='product_variant.discounted_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_variant_id', 'product_variant', 'product_name', 'product_image', 'quantity', 'price', 'discounted_price']

    def get_product_image(self, obj):
        image = obj.product_variant.product.images.first()
        return image.image if image else None


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    status = serializers.StringRelatedField()
    items = OrderItemSerializer(many=True, read_only=True)
    payment_status = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()
    delivery_person = DeliveryPersonSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'status', 'order_id', 'payment_method', 'tracking_link',
            'delivery_schedule_id', 'delivery_date', 'delivery_slot_name',
            'slot_start_time', 'slot_end_time',
            'delivery_person', 'created_at', 'items', 'address', 
            'total_amount', 'taxes', 'handling_charges', 'delivery_charges', 'final_amount',
            'payment_status', 'payment_amount'
        ]

    def _get_payment(self, obj):
        # Use prefetched payment_set if available (set via prefetch_related('payment_set') in the view)
        # This eliminates the N+1: instead of 1 query per order, Django fetches all payments in 1 query.
        prefetched = getattr(obj, '_prefetched_objects_cache', {})
        if 'payment_set' in prefetched:
            payments = prefetched['payment_set']
            return payments[0] if payments else None
        # Fallback: single object cache for non-prefetched calls (e.g. retrieve())
        if not hasattr(obj, '_cached_payment'):
            obj._cached_payment = Payment.objects.filter(order=obj).first()
        return obj._cached_payment

    def get_payment_status(self, obj):
        payment = self._get_payment(obj)
        return payment.status if payment else None

    def get_payment_amount(self, obj):
        payment = self._get_payment(obj)
        return payment.amount if payment else None


# ── Admin-only serializers (no product_image for lighter responses) ──────────

class AdminOrderItemSerializer(serializers.ModelSerializer):
    """Like OrderItemSerializer but excludes product_image."""
    product_variant_id = serializers.IntegerField(source='product_variant.id', read_only=True)
    product_variant = serializers.StringRelatedField()
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discounted_price = serializers.DecimalField(source='product_variant.discounted_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_variant_id', 'product_variant', 'product_name', 'quantity', 'price', 'discounted_price']


class AdminOrderSerializer(serializers.ModelSerializer):
    """Order serializer for admin endpoints — items have no product_image."""
    user = serializers.StringRelatedField()
    status = serializers.StringRelatedField()
    items = AdminOrderItemSerializer(many=True, read_only=True)
    payment_status = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()
    delivery_person = DeliveryPersonSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'status', 'order_id', 'payment_method', 'tracking_link',
            'delivery_schedule_id', 'delivery_date', 'delivery_slot_name',
            'slot_start_time', 'slot_end_time',
            'delivery_person', 'created_at', 'items', 'address', 
            'total_amount', 'taxes', 'handling_charges', 'delivery_charges', 'final_amount',
            'payment_status', 'payment_amount'
        ]

    def _get_payment(self, obj):
        prefetched = getattr(obj, '_prefetched_objects_cache', {})
        if 'payment_set' in prefetched:
            payments = prefetched['payment_set']
            return payments[0] if payments else None
        if not hasattr(obj, '_cached_payment'):
            obj._cached_payment = Payment.objects.filter(order=obj).first()
        return obj._cached_payment

    def get_payment_status(self, obj):
        payment = self._get_payment(obj)
        return payment.status if payment else None

    def get_payment_amount(self, obj):
        payment = self._get_payment(obj)
        return payment.amount if payment else None


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    status = serializers.PrimaryKeyRelatedField(queryset=OrderStatus.objects.all(), required=False)
    delivery_person = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryPerson.objects.all(),
        required=False,
        allow_null=True,
    )
    # tracking_link removed

    class Meta:
        model = Order
        fields = ['status', 'delivery_person']

    def validate_delivery_person(self, value):
        if value and not value.can_receive_orders:
            raise serializers.ValidationError(
                'Delivery person must be active and have a completed profile.'
            )
        return value

    def update(self, instance, validated_data):
        if validated_data.get('delivery_person') and 'status' not in validated_data:
            assigned_status, _ = OrderStatus.objects.get_or_create(
                name='Assign to Delivery Partner'
            )
            validated_data['status'] = assigned_status
        return super().update(instance, validated_data)


class DeliveryOrderSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='status.name', read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_mobile = serializers.SerializerMethodField()
    address = AddressSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'payment_method', 'delivery_date',
            'delivery_slot_name', 'slot_start_time', 'slot_end_time',
            'customer_name', 'customer_mobile', 'address', 'items',
            'final_amount', 'created_at',
        ]
        read_only_fields = fields

    def get_customer_name(self, obj):
        if obj.address and obj.address.full_name:
            return obj.address.full_name
        if obj.user:
            return obj.user.get_full_name().strip() or obj.user.first_name
        return None

    def get_customer_mobile(self, obj):
        if obj.address and obj.address.mobile:
            return obj.address.mobile
        return obj.user.mobile if obj.user else None


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = '__all__'
