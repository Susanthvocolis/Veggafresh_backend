from rest_framework import serializers
from .models import Cart, CartItem

class CartItemSerializer(serializers.ModelSerializer):
    cart_item_id = serializers.IntegerField(source='id', read_only=True)
    product_id = serializers.IntegerField(source='product_variant.product.id', read_only=True)
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    product_variant_id = serializers.IntegerField(source='product_variant.id', read_only=True)
    product_variant = serializers.StringRelatedField()
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'cart_item_id',
            'product_id',
            'product_name',
            'product_variant_id',
            'product_variant',
            'product_image',
            'quantity',
        ]

    def get_product_image(self, obj):
        image = obj.product_variant.product.images.first()
        return image.image if image else None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id',
            'user',
            'items',
            'total_amount',
            'taxes',
            'handling_charges',
            'delivery_charges',
            'final_amount',
        ]
