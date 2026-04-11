from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from address.models import Address
from cart.models import Cart, CartItem
from cart.serializers import CartSerializer
from orders.models import Order
from orders.serializers import OrderSerializer


class MyOrdersView(APIView):
    """
    GET /api/v1/my-orders/
    Returns the authenticated user's orders, newest first.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects
            .filter(user=request.user)
            .select_related('status', 'delivery_person', 'address')
            .prefetch_related(
                'items__product_variant__product__images',
                'payment_set',   # eliminates Payment N+1
            )
            .order_by('-created_at')
        )
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class MyOrderDetailView(APIView):
    """
    GET /api/v1/my-orders/<order_id>/
    Returns full detail of a single order belonging to the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = (
                Order.objects
                .select_related('status', 'delivery_person', 'address')
                .prefetch_related(
                    'items__product_variant__product__images',
                    'payment_set',   # eliminates Payment N+1
                )
                .get(order_id=order_id, user=request.user)
            )
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order)
        return Response(serializer.data)


class ReorderView(APIView):
    """
    POST /api/v1/my-orders/<order_id>/reorder/
    Adds all items from a previous order back into the user's current cart.
    Skips variants that are no longer available.
    Returns the updated cart.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = (
                Order.objects
                .prefetch_related('items__product_variant__product')
                .get(order_id=order_id, user=request.user)
            )
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        added = []
        skipped = []

        for item in order.items.all():
            variant = item.product_variant
            if not variant.is_available or variant.stock < 1:
                skipped.append({
                    'product': variant.product.name,
                    'reason': 'Out of stock or unavailable',
                })
                continue

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product_variant=variant,
            )
            if created:
                cart_item.quantity = item.quantity
            else:
                cart_item.quantity += item.quantity
            cart_item.save()
            added.append(variant.product.name)

        cart.calculate_totals()

        return Response({
            'message': 'Items added to cart.',
            'added': added,
            'skipped': skipped,
            'cart': CartSerializer(cart).data,
        }, status=status.HTTP_200_OK)
