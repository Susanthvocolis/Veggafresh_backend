from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import filters
from orders.filters import OrderFilter
from orders.models import Order, OrderStatus, DeliveryPerson
from orders.permissions import IsSuperAdminOrHasOrderPermission
from orders.serializers import OrderSerializer, OrderStatusUpdateSerializer, OrderStatusSerializer, \
    DeliveryPersonSerializer, AdminOrderSerializer
from users.services import send_order_placed_sms, send_out_for_delivery_sms
from utils.pagination import CustomPageNumberPagination

class AdminFilterOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related('status', 'user', 'delivery_person').order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [IsSuperAdminOrHasOrderPermission]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter  # This ties the filter class to your viewset
    search_fields = ['order_id', 'status__name']  # Add any additional search fields here
    ordering_fields = ['created_at']
    ordering = ['-created_at']  # Default: newest orders first
class GetAllOrderViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperAdminOrHasOrderPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter  # This ties the filter class to your viewset
    search_fields = ['order_id', 'status__name']  # Add any additional search fields here
    ordering_fields = ['created_at']
    ordering = ['-created_at']  # Default: newest orders first

    def list(self, request, *args, **kwargs):
        # Get filters and page parameters from the request
        page_no = int(request.query_params.get('page_no', 1))
        page_size = int(request.query_params.get('page_size', 100))

        # Apply filters (using the same query as in your filterset)
        queryset = Order.objects.all().select_related('status', 'user', 'delivery_person').order_by('-created_at')

        # Get the filtered count
        total_count = queryset.count()

        # Pagination logic - Calculate the data to return based on page_no and page_size
        start = (page_no - 1) * page_size
        end = start + page_size
        queryset = queryset[start:end]  # Slice the queryset

        # Serialize the data
        serializer = OrderSerializer(queryset, many=True)

        # Return paginated data with count
        return Response({
            'count': total_count,
            'page_no': page_no,
            'page_size': page_size,
            'results': serializer.data
        })


class AdminOrderViewSet(viewsets.ViewSet):
    """
    GET /api/v1/orders/
    Supports filtering, searching, sorting, and pagination.

    Filter params:
      ?order_id=          — partial match on order ID
      ?status=            — partial match on status name (e.g. Accepted, Cancelled)
      ?user_id=           — exact user ID
      ?user_email=        — partial match on user email
      ?user_mobile=       — partial match on user mobile
      ?payment_method=    — 'online' or 'cod'
      ?order_date_from=   — YYYY-MM-DD (created_at >= date)
      ?order_date_to=     — YYYY-MM-DD (created_at <= date)

    Search param:
      ?search=            — searches order_id and status name

    Sort param:
      ?ordering=created_at     — oldest first
      ?ordering=-created_at    — newest first (default)
      ?ordering=payment_method — sort by payment type

    Pagination params:
      ?page_no=           — page number (default: 1)
      ?page_size=         — items per page (default: 10, max: 100)
    """
    permission_classes = [IsSuperAdminOrHasOrderPermission]

    # Declare backends so DRF schema / browsable API picks them up
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['order_id', 'status__name']
    ordering_fields = ['created_at', 'payment_method']
    ordering = ['-created_at']

    def _get_queryset(self, request):
        """Build and return the filtered + sorted queryset for the request."""
        queryset = (
            Order.objects
            .all()
            .select_related('status', 'user', 'delivery_person')
            .order_by('-created_at')
        )

        # Apply DjangoFilterBackend (uses OrderFilter: status, user, date range, order_id)
        queryset = DjangoFilterBackend().filter_queryset(request, queryset, self)

        # Apply SearchFilter (?search=)
        queryset = filters.SearchFilter().filter_queryset(request, queryset, self)

        # Apply OrderingFilter (?ordering=)
        queryset = filters.OrderingFilter().filter_queryset(request, queryset, self)

        # Extra: filter by payment_method directly (?payment_method=online|cod)
        payment_method = request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method__iexact=payment_method)

        return queryset

    def list(self, request):
        queryset = self._get_queryset(request)
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminOrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            order = Order.objects.select_related('status', 'user', 'delivery_person').get(pk=pk)
            serializer = AdminOrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found'}, status=404)

    def destroy(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
            order.delete()
            return Response({"message": "Order deleted successfully"}, status=204)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=404)

    @action(detail=False, methods=['get'], url_path='status/(?P<status_name>[^/.]+)')
    def get_by_status(self, request, status_name=None):
        orders = Order.objects.filter(status__name__iexact=status_name).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found'}, status=404)

        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            order.refresh_from_db()

            msg_map = {
                "Accepted": "Order has been accepted.",
                "Cancelled": "Order has been cancelled. Sorry for the inconvenience.",
                "Assign to Delivery Partner": "Order assigned to delivery partner.",
                "Out For Delivery": "Order is out for delivery.",
                "Delivery Status Update": "Thank you! Order has been marked as delivered."
            }
            message = msg_map.get(order.status.name, "Order updated.")

            if order.status.name == "Out For Delivery":
                user = order.user
                if user and user.mobile:
                    try:
                        send_out_for_delivery_sms(
                            mobile=user.mobile,
                            user_name=user.first_name or "Customer",
                            order_id=order.order_id,
                        )
                    except Exception as e:
                        print(f"Out for delivery SMS failed: {e}")

            return Response({
                "message": message,
                "data": OrderSerializer(order).data,
                "status_code": 200
            })

        return Response({
            "message": "Failed",
            "data": serializer.errors,
            "status_code": 400
        }, status=400)

    @action(detail=False, methods=['get'], url_path='status-options')
    def status_options(self, request):
        msg_map = {
            "Accepted": "Order has been accepted.",
            "Cancelled": "Order has been cancelled. Sorry for the inconvenience.",
            "Assign to Delivery Partner": "Order assigned to delivery partner.",
            "Out For Delivery": "Order is out for delivery.",
            "Delivery Status Update": "Thank you! Order has been marked as delivered.",
        }

        statuses = [
            {
                "id": s["id"],
                "name": s["name"],
                "message": msg_map.get(s["name"], "Order status updated."),
            }
            for s in OrderStatus.objects.all().values("id", "name")
        ]
        return Response({"status_options": statuses})
class UserOrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']  # Default: newest orders first

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        order = serializer.save(user=self.request.user)
        user = self.request.user
        if user.mobile:
            try:
                send_order_placed_sms(
                    mobile=user.mobile,
                    user_name=user.first_name or "Customer",
                    order_id=order.order_id,
                    total_amount=order.final_amount,
                )
            except Exception as e:
                print(f"Order placed SMS failed: {e}")

class OrderStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer

class DeliveryPersonViewSet(viewsets.ModelViewSet):
    queryset = DeliveryPerson.objects.all()
    serializer_class = DeliveryPersonSerializer
    permission_classes = [IsAuthenticated]


# Message shown to customer for each order status
ORDER_STATUS_MESSAGES = {
    "Accepted": "Order has been accepted.",
    "Cancelled": "Order has been cancelled. Sorry for the inconvenience.",
    "Assign to Delivery Partner": "Order assigned to delivery partner.",
    "Out For Delivery": "Order is out for delivery.",
    "Delivery Status Update": "Thank you! Order has been marked as delivered.",
}


class OrderStatusListView(APIView):
    """
    GET /api/v1/order-statuses/
    Returns all order statuses with their id, name, and customer-facing message.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        statuses = [
            {
                "id": s["id"],
                "name": s["name"],
                "message": ORDER_STATUS_MESSAGES.get(s["name"], "Order status updated."),
            }
            for s in OrderStatus.objects.all().values("id", "name")
        ]
        return Response({"status_options": statuses})