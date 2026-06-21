from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeliverySchedule, DeliverySlot
from .permissions import IsSuperAdminOrCanManageDelivery
from .serializers import (
    DeliveryScheduleGenerateSerializer,
    DeliveryScheduleSerializer,
    DeliverySlotSerializer,
)


class DeliverySlotViewSet(viewsets.ModelViewSet):
    queryset = DeliverySlot.objects.all()
    serializer_class = DeliverySlotSerializer
    permission_classes = [IsSuperAdminOrCanManageDelivery]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'start_time', 'end_time', 'created_at']
    ordering = ['sort_order', 'start_time']


class DeliveryScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = DeliveryScheduleSerializer
    permission_classes = [IsSuperAdminOrCanManageDelivery]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['delivery_date', 'slot', 'is_active', 'is_blocked']
    search_fields = ['slot__name']
    ordering_fields = ['delivery_date', 'slot__start_time', 'max_orders', 'booked_orders', 'created_at']
    ordering = ['delivery_date', 'slot__sort_order', 'slot__start_time']

    def get_queryset(self):
        return DeliverySchedule.objects.select_related('slot').all()

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        serializer = DeliveryScheduleGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({
            "message": "Delivery schedules generated successfully.",
            **result,
        }, status=status.HTTP_201_CREATED)


class CustomerDeliverySlotsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        slots = DeliverySlot.objects.filter(is_active=True).order_by('sort_order', 'start_time', 'name')
        serializer = DeliverySlotSerializer(slots, many=True)
        return Response({"slots": serializer.data})
