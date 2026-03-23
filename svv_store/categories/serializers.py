import base64

from rest_framework import serializers

from .models import Category, SubCategory


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


class SimpleSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ('id', 'name')


class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = SubCategory
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True},
            'created_by': {'read_only': True},
            'updated_by': {'read_only': True},
            'image': {'required': False},
        }


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SimpleSubCategorySerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Category
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True},
            'created_by': {'read_only': True},
            'updated_by': {'read_only': True},
            'image': {'required': False},
        }
