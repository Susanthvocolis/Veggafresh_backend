from rest_framework import serializers

from utils.signed_url import generate_signed_token
from .models import Product, ProductVariant, ProductImage
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlencode
import hashlib
import hmac
import base64

from django.urls import reverse

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['quantity', 'unit', 'price', 'discounted_price', 'stock', 'is_available']
        extra_kwargs = {
            'discounted_price': {'required': False},
        }


class ProductImageSerializer(serializers.ModelSerializer):
    secure_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'alt_text', 'secure_url']

    def get_secure_url(self, obj):
        if not obj.image:
            return None
        token = generate_signed_token(obj.image.name)
        return self.context['request'].build_absolute_uri(
            reverse('secure-media', kwargs={'token': token})
        )


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True)
    images = ProductImageSerializer(many=True, required=False)
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'subcategory', 'brand',
            'is_active', 'variants', 'images','category_name', 'subcategory_name'
        ]
        read_only_fields = ['slug','category_name', 'subcategory_name']
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'brand': {'required': False, 'allow_blank': True},
            'is_active': {'required': False},
        }

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None
    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        images_data = validated_data.pop('images', [])
        request = self.context.get('request')
        user = request.user if request else None

        # Set default values for optional fields
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        if 'description' not in validated_data:
            validated_data['description'] = ''
        if 'brand' not in validated_data:
            validated_data['brand'] = ''

        product = Product.objects.create(**validated_data, created_by=user, updated_by=user)

        for variant in variants_data:
            # Handle empty discounted_price
            if 'discounted_price' not in variant or variant['discounted_price'] == '':
                variant['discounted_price'] = None

            ProductVariant.objects.create(product=product, **variant)

        for image in images_data:
            if 'alt_text' not in image:
                image['alt_text'] = ''
            ProductImage.objects.create(product=product, created_by=user, updated_by=user, **image)

        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', None)
        images_data = validated_data.pop('images', None)
        request = self.context.get('request')
        user = request.user if request else None

        # Update basic product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update updated_by field
        instance.updated_by = user
        instance.save()

        # Update variants if provided
        if variants_data is not None:
            # Remove existing variants
            instance.variants.all().delete()

            # Create new variants
            for variant in variants_data:
                if 'discounted_price' not in variant or variant['discounted_price'] == '':
                    variant['discounted_price'] = None
                ProductVariant.objects.create(product=instance, **variant)

        # Add new images if provided
        if images_data:
            for image in images_data:
                if 'alt_text' not in image:
                    image['alt_text'] = ''
                ProductImage.objects.create(
                    product=instance,
                    created_by=user,
                    updated_by=user,
                    **image
                )

        return instance

class UserProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True)
    images = ProductImageSerializer(many=True, required=False)
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'subcategory', 'brand',
            'is_active', 'variants', 'images', 'category_name', 'subcategory_name'
        ]
        read_only_fields = ['slug', 'category_name', 'subcategory_name']
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'brand': {'required': False, 'allow_blank': True},
            'is_active': {'required': False},
        }

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None
