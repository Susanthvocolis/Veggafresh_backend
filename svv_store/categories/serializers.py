from rest_framework import serializers
from .models import Category, SubCategory
from rest_framework import serializers
from .models import Category, SubCategory

class SimpleSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ('id', 'name')

class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = SubCategory
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True},
            'created_by': {'read_only': True},
            'updated_by': {'read_only': True},
            'image': {'required': False}
        }

class CategorySerializer(serializers.ModelSerializer):
    subcategories = SimpleSubCategorySerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()
    updated_by = serializers.StringRelatedField()
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Category
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True},
            'created_by': {'read_only': True},
            'updated_by': {'read_only': True},
            'image': {'required': False}
        }
