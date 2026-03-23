from rest_framework import serializers
from .models import Wishlist


class WishlistSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    brand = serializers.CharField(source='product.brand', read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ['id', 'product_id', 'product_name', 'product_slug', 'brand', 'product_image', 'created_at']

    def get_product_image(self, obj):
        image = obj.product.images.first()
        return image.image if image else None
