from rest_framework import serializers

from address.serializers import AddressSerializer
from payments.models import Payment
from .models import Order, OrderItem, OrderStatus, DeliveryPerson


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product_variant', 'quantity']


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = ['items']

    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data.pop('items')

        status = OrderStatus.objects.get(name="Pending")
        order = Order.objects.create(user=user, status=status, **validated_data)

        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)

        return order


class OrderItemSerializer(serializers.ModelSerializer):
    product_variant_id = serializers.IntegerField(source='product_variant.id', read_only=True)
    product_variant = serializers.StringRelatedField()
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    price = serializers.DecimalField(source='product_variant.price', max_digits=10, decimal_places=2, read_only=True)
    discounted_price = serializers.DecimalField(source='product_variant.discounted_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_variant_id', 'product_variant', 'product_name', 'product_image', 'quantity', 'price', 'discounted_price']

    def get_product_image(self, obj):
        image = obj.product_variant.product.images.first()
        return image.image if image else None


class DeliveryPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPerson
        fields = ['id', 'name', 'mobile']


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
            'delivery_person', 'created_at', 'items', 'address', 'final_amount',
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


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    status = serializers.PrimaryKeyRelatedField(queryset=OrderStatus.objects.all())
    # delivery_person = serializers.PrimaryKeyRelatedField(
    #     queryset=DeliveryPerson.objects.all(), required=False
    # )
    # tracking_link removed

    class Meta:
        model = Order
        fields = ['status']  # only status is updated


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = '__all__'
