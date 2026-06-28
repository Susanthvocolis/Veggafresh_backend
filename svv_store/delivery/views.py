from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from orders.models import Order, OrderStatus
from orders.serializers import AdminOrderSerializer, DeliveryOrderSerializer
from users.models import User
from users.services import send_out_for_delivery_sms
from .models import DeliveryPerson, DeliverySchedule, DeliverySlot
from .permissions import IsDeliveryPerson, IsSuperAdminOrCanManageDelivery
from .serializers import (
    AssignDeliverySlotSerializer,
    DeliveryPersonAdminSerializer,
    DeliveryPersonProfileUpdateSerializer,
    DeliveryPersonSerializer,
    DeliveryScheduleGenerateSerializer,
    DeliveryScheduleSerializer,
    DeliverySlotSerializer,
)


class DeliveryPersonLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if not user or user.role != User.Role.DELIVERY_PERSON:
            return Response(
                {'error': 'Invalid credentials or unauthorized access.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not hasattr(user, 'delivery_profile'):
            return Response(
                {'error': 'Delivery profile is not configured.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'profile_complete': user.profile_complete,
            'delivery_person': DeliveryPersonSerializer(user.delivery_profile).data,
        })


class DeliveryPersonAdminViewSet(viewsets.ModelViewSet):
    serializer_class = DeliveryPersonAdminSerializer
    permission_classes = [IsAuthenticated, IsSuperAdminOrCanManageDelivery]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['user__first_name', 'user__email', 'user__mobile', 'vehicle_number']
    ordering_fields = ['user__first_name', 'user__mobile', 'status', 'created_at']
    ordering = ['user__first_name']

    def get_queryset(self):
        return DeliveryPerson.objects.select_related('user').all()


class DeliveryPersonProfileView(APIView):
    permission_classes = [IsAuthenticated, IsDeliveryPerson]

    def get(self, request):
        return Response(DeliveryPersonSerializer(request.user.delivery_profile).data)

    def patch(self, request):
        profile = request.user.delivery_profile
        serializer = DeliveryPersonProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Delivery profile updated successfully.',
            'delivery_person': DeliveryPersonSerializer(profile).data,
        })


class DeliveryPersonOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliveryOrderSerializer
    permission_classes = [IsAuthenticated, IsDeliveryPerson]
    lookup_field = 'order_id'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'delivery_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            Order.objects
            .filter(delivery_person=self.request.user.delivery_profile)
            .select_related('status', 'user', 'address', 'delivery_schedule')
            .prefetch_related('items__product_variant__product__images')
        )

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, order_id=None):
        order = self.get_object()
        requested_status = request.data.get('status')
        if isinstance(requested_status, int) or (
            isinstance(requested_status, str) and requested_status.isdigit()
        ):
            target_status = OrderStatus.objects.filter(pk=requested_status).first()
        else:
            target_status = OrderStatus.objects.filter(name__iexact=requested_status or '').first()

        if not target_status:
            return Response({'error': 'Invalid order status.'}, status=status.HTTP_400_BAD_REQUEST)

        current_name = order.status.name if order.status else None
        target_name = target_status.name
        allowed_transitions = {
            'Assign to Delivery Partner': {'Out For Delivery'},
            'Out For Delivery': {'Delivered'},
        }
        if target_name not in allowed_transitions.get(current_name, set()):
            return Response(
                {'error': f'Cannot change status from {current_name} to {target_name}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            order.status = target_status
            order.save(update_fields=['status'])

        if target_name == 'Out For Delivery' and order.user and order.user.mobile:
            try:
                send_out_for_delivery_sms(
                    mobile=order.user.mobile,
                    user_name=order.user.first_name or 'Customer',
                    order_id=order.order_id,
                )
            except Exception as exc:
                print(f'Out for delivery SMS failed: {exc}')

        return Response({
            'message': f'Order marked as {target_name}.',
            'order': DeliveryOrderSerializer(order).data,
        })


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


class AdminAssignDeliveryView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdminOrCanManageDelivery]

    def post(self, request):
        serializer = AssignDeliverySlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response({
            "message": "Delivery person assigned successfully.",
            "data": AdminOrderSerializer(order).data,
        }, status=status.HTTP_200_OK)


class CustomerDeliverySlotsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        slots = DeliverySlot.objects.filter(is_active=True).order_by('sort_order', 'start_time', 'name')
        serializer = DeliverySlotSerializer(slots, many=True)
        return Response({"slots": serializer.data})
