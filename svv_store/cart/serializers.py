from rest_framework import serializers
from .models import Cart, CartItem
from products.models import ProductVariant

class CartItemSerializer(serializers.ModelSerializer):
    product_variant = serializers.StringRelatedField()

    class Meta:
        model = CartItem
        fields = ['id', 'product_variant', 'quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_amount', 'taxes', 'handling_charges', 'delivery_charges', 'final_amount']