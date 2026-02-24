from rest_framework import serializers
from .models import Wishlist
from products.models import Product

class WishlistSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    brand = serializers.CharField(source='product.brand', read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product_id', 'product_name', 'product_slug', 'brand', 'created_at']
