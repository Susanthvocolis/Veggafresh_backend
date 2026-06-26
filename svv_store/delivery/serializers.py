from collections import OrderedDict
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from django.db import transaction

from users.models import User
from .models import DeliveryPerson, DeliverySchedule, DeliverySlot


class DeliveryPersonSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.first_name')
    mobile = serializers.CharField(source='user.mobile')
    email = serializers.EmailField(source='user.email')
    profile_complete = serializers.BooleanField(source='user.profile_complete', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)

    class Meta:
        model = DeliveryPerson
        fields = [
            'id', 'name', 'mobile', 'email', 'vehicle_type', 'vehicle_number',
            'address', 'status', 'profile_complete', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class DeliveryPersonAdminSerializer(DeliveryPersonSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    is_active = serializers.BooleanField(source='user.is_active', required=False)

    class Meta(DeliveryPersonSerializer.Meta):
        fields = DeliveryPersonSerializer.Meta.fields + ['password']

    def validate(self, attrs):
        user_data = attrs.get('user', {})
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Password is required.'})

        mobile = user_data.get('mobile')
        email = user_data.get('email')
        user_queryset = User.objects.all()
        if self.instance:
            user_queryset = user_queryset.exclude(pk=self.instance.user_id)
        if mobile and user_queryset.filter(mobile=mobile).exists():
            raise serializers.ValidationError({'mobile': 'A user with this mobile already exists.'})
        if email and user_queryset.filter(email__iexact=email).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password = validated_data.pop('password')
        name = user_data.pop('first_name')
        user = User(
            first_name=name,
            username=user_data.get('mobile'),
            role=User.Role.DELIVERY_PERSON,
            profile_complete=False,
            **user_data,
        )
        user.set_password(password)
        user.save()
        instance = DeliveryPerson.objects.create(user=user, **validated_data)
        self._update_profile_complete(instance)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        password = validated_data.pop('password', None)
        user = instance.user
        for field, value in user_data.items():
            setattr(user, field, value)
        if user.mobile:
            user.username = user.mobile
        if password:
            user.set_password(password)
        user.save()

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        self._update_profile_complete(instance)
        return instance

    @staticmethod
    def _update_profile_complete(instance):
        user = instance.user
        complete = all([
            user.first_name,
            user.mobile,
            user.email,
            instance.vehicle_type,
            instance.vehicle_number,
            instance.address,
        ])
        if user.profile_complete != bool(complete):
            user.profile_complete = bool(complete)
            user.save(update_fields=['profile_complete'])


class DeliveryPersonProfileUpdateSerializer(DeliveryPersonSerializer):
    mobile = serializers.CharField(source='user.mobile', read_only=True)

    class Meta(DeliveryPersonSerializer.Meta):
        read_only_fields = ['mobile', 'created_at', 'updated_at', 'profile_complete', 'is_active']

    def validate_email(self, value):
        if User.objects.exclude(pk=self.instance.user_id).filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        for field, value in user_data.items():
            setattr(user, field, value)
        user.save()

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        DeliveryPersonAdminSerializer._update_profile_complete(instance)
        return instance


class DeliverySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverySlot
        fields = [
            'id', 'name', 'start_time', 'end_time', 'is_active',
            'sort_order', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        start_time = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({"end_time": "Must be after start_time."})
        return attrs


class DeliveryScheduleSerializer(serializers.ModelSerializer):
    slot_name = serializers.CharField(source='slot.name', read_only=True)
    slot_start_time = serializers.TimeField(source='slot.start_time', read_only=True)
    slot_end_time = serializers.TimeField(source='slot.end_time', read_only=True)
    available_capacity = serializers.IntegerField(read_only=True)
    availability_status = serializers.SerializerMethodField()

    class Meta:
        model = DeliverySchedule
        fields = [
            'id', 'delivery_date', 'slot', 'slot_name', 'slot_start_time',
            'slot_end_time', 'max_orders', 'booked_orders', 'available_capacity',
            'is_active', 'is_blocked', 'availability_status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        max_orders = attrs.get('max_orders', getattr(self.instance, 'max_orders', 0))
        booked_orders = attrs.get('booked_orders', getattr(self.instance, 'booked_orders', 0))
        if booked_orders > max_orders:
            raise serializers.ValidationError({"booked_orders": "Cannot be greater than max_orders."})
        return attrs

    def get_availability_status(self, obj):
        if not obj.is_active:
            return "inactive"
        if obj.is_blocked:
            return "blocked"
        if not obj.slot.is_active:
            return "slot_inactive"
        if obj.booked_orders >= obj.max_orders:
            return "full"
        return "available"


class DeliveryScheduleGenerateSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    days = serializers.IntegerField(min_value=1, max_value=365, default=30)
    default_capacity = serializers.IntegerField(min_value=0)
    slot_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        required=False,
    )

    def validate(self, attrs):
        attrs['start_date'] = attrs.get('start_date') or timezone.localdate()
        slot_ids = attrs.get('slot_ids')
        slots = DeliverySlot.objects.filter(is_active=True)
        if slot_ids:
            slots = slots.filter(id__in=slot_ids)
        slots = list(slots)
        if not slots:
            raise serializers.ValidationError({"slot_ids": "No active delivery slots found."})
        attrs['slots'] = slots
        return attrs

    def create(self, validated_data):
        start_date = validated_data['start_date']
        days = validated_data['days']
        default_capacity = validated_data['default_capacity']
        slots = validated_data['slots']

        created = []
        existing = 0
        for offset in range(days):
            delivery_date = start_date + timedelta(days=offset)
            for slot in slots:
                schedule, was_created = DeliverySchedule.objects.get_or_create(
                    delivery_date=delivery_date,
                    slot=slot,
                    defaults={
                        'max_orders': default_capacity,
                        'booked_orders': 0,
                        'is_active': True,
                        'is_blocked': False,
                    },
                )
                if was_created:
                    created.append(schedule)
                else:
                    existing += 1

        return {
            'created_count': len(created),
            'existing_count': existing,
            'created_ids': [schedule.id for schedule in created],
        }


class CustomerDeliverySlotSerializer:
    @staticmethod
    def serialize(options):
        grouped = OrderedDict()
        for option in options:
            date_key = option['date'].isoformat()
            grouped.setdefault(date_key, [])
            grouped[date_key].append({
                "schedule_id": option['schedule_id'],
                "slot_id": option['slot_id'],
                "slot_name": option['slot_name'],
                "start_time": option['start_time'].strftime("%H:%M"),
                "end_time": option['end_time'].strftime("%H:%M"),
                "available_capacity": option['available_capacity'],
            })

        return {
            "delivery_dates": [
                {"date": date, "slots": slots}
                for date, slots in grouped.items()
            ]
        }
