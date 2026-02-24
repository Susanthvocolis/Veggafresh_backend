from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import filters
from orders.filters import OrderFilter
from orders.models import Order, OrderStatus, DeliveryPerson
from orders.permissions import IsSuperAdminOrHasOrderPermission
from orders.serializers import OrderSerializer, OrderStatusUpdateSerializer, OrderStatusSerializer, \
    DeliveryPersonSerializer

class AdminFilterOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related('status', 'user', 'delivery_person').order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [IsSuperAdminOrHasOrderPermission]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter  # This ties the filter class to your viewset
    search_fields = ['order_id', 'status__name']  # Add any additional search fields here
    ordering_fields = ['created_at']
class GetAllOrderViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperAdminOrHasOrderPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter  # This ties the filter class to your viewset
    search_fields = ['order_id', 'status__name']  # Add any additional search fields here
    ordering_fields = ['created_at']

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
    permission_classes = [IsSuperAdminOrHasOrderPermission]
    def list(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
            serializer = OrderSerializer(order)
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
        orders = Order.objects.filter(status__name__iexact=status_name)
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

            msg_map = {
                "Accepted": "Order has been accepted.",
                "Cancelled": "Order has been cancelled. Sorry for the inconvenience.",
                "Assign to Delivery Partner": "Order assigned to delivery partner.",
                "Delivery Status Update": "Thank you! Order has been marked as delivered."
            }
            message = msg_map.get(order.status.name, "Order updated.")

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
        statuses = OrderStatus.objects.all().values('id', 'name')
        return Response({"status_options": list(statuses)})
class UserOrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class OrderStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer

class DeliveryPersonViewSet(viewsets.ModelViewSet):
    queryset = DeliveryPerson.objects.all()
    serializer_class = DeliveryPersonSerializer
    permission_classes = [IsAuthenticated]