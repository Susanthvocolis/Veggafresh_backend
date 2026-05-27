from rest_framework import serializers
from .models import Banner


class BannerSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'subtitle', 'image', 'mobile_image',
            'link_url', 'banner_type', 'position', 'is_active',
            'start_date', 'end_date',
            'created_by', 'updated_by', 'created_by_name', 'updated_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'updated_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.email
        return None


class PublicBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'subtitle', 'image', 'mobile_image',
            'link_url', 'banner_type', 'position',
        ]
