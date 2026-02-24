from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem
from .serializers import CartSerializer
from products.models import ProductVariant

class CartViewSet(viewsets.ViewSet):

    def list(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def create(self, request):
        product_variant_id = request.data.get('product_variant_id')
        quantity = int(request.data.get('quantity', 1))

        try:
            product_variant = ProductVariant.objects.get(id=product_variant_id)
        except ProductVariant.DoesNotExist:
            return Response({'error': 'Product variant not found'}, status=404)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product_variant=product_variant)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

        cart.calculate_totals()
        return Response(CartSerializer(cart).data, status=201)

    def destroy(self, request, pk=None):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response({'error': 'Cart not found'}, status=404)
        try:
            item = cart.items.get(id=pk)
            item.delete()
            cart.calculate_totals()
            return Response({'message': 'Item removed successfully'})
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=404)
