from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_variant = serializers.StringRelatedField()
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product_variant', 'product_name', 'product_image', 'quantity']

    def get_product_image(self, obj):
        image = obj.product_variant.product.images.first()
        return image.image if image else None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_amount', 'taxes', 'handling_charges', 'delivery_charges', 'final_amount']
