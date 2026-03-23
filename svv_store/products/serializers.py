import base64

from rest_framework import serializers

from .models import Product, ProductVariant, ProductImage


class Base64ImageField(serializers.Field):
    """
    Accepts a file upload (multipart) on write — converts it to a base64 data URI.
    Returns the stored base64 string as-is on read.
    """

    def to_internal_value(self, data):
        if isinstance(data, str):
            # Already a base64 string (e.g. sent back unchanged by FE)
            return data
        try:
            content = data.read()
            mime_type = getattr(data, 'content_type', None) or 'image/jpeg'
            encoded = base64.b64encode(content).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"
        except Exception:
            raise serializers.ValidationError("Invalid image file.")

    def to_representation(self, value):
        return value


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['quantity', 'unit', 'price', 'discounted_price', 'stock', 'is_available']
        extra_kwargs = {
            'discounted_price': {'required': False},
        }


class ProductImageSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = ProductImage
        fields = ['id', 'alt_text', 'image']


class ProductSerializer(serializers.ModelSerializer):
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

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        images_data = validated_data.pop('images', [])
        request = self.context.get('request')
        user = request.user if request else None

        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        if 'description' not in validated_data:
            validated_data['description'] = ''
        if 'brand' not in validated_data:
            validated_data['brand'] = ''

        product = Product.objects.create(**validated_data, created_by=user, updated_by=user)

        for variant in variants_data:
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

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.updated_by = user
        instance.save()

        if variants_data is not None:
            instance.variants.all().delete()
            for variant in variants_data:
                if 'discounted_price' not in variant or variant['discounted_price'] == '':
                    variant['discounted_price'] = None
                ProductVariant.objects.create(product=instance, **variant)

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
