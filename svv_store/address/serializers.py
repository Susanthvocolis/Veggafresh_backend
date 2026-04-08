from rest_framework import serializers
from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for user-facing address CRUD."""

    class Meta:
        model = Address
        fields = [
            'id', 'full_name', 'mobile', 'pincode',
            'address_line1', 'address_line2', 'landmark',
            'city', 'state', 'country',
            'latitude', 'longitude',
            'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class AdminAddressSerializer(serializers.ModelSerializer):
    """Serializer for admin-facing address APIs — includes user info."""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.SerializerMethodField()
    user_mobile = serializers.CharField(source='user.mobile', read_only=True)

    class Meta:
        model = Address
        fields = [
            'id', 'user_id', 'user_name', 'user_mobile',
            'full_name', 'mobile', 'pincode',
            'address_line1', 'address_line2', 'landmark',
            'city', 'state', 'country',
            'latitude', 'longitude',
            'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = fields  # admin view is read-only

    def get_user_name(self, obj):
        parts = [obj.user.first_name, obj.user.last_name]
        return ' '.join(p for p in parts if p) or None
