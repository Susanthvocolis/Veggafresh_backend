from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminAssignDeliveryView,
    CustomerDeliverySlotsView,
    DeliveryPersonAdminViewSet,
    DeliveryPersonLoginView,
    DeliveryPersonOrderViewSet,
    DeliveryPersonProfileView,
    DeliveryScheduleViewSet,
    DeliverySlotViewSet,
)


router = DefaultRouter()
router.register(r'admin/delivery-slots', DeliverySlotViewSet, basename='delivery-slots')
router.register(r'admin/delivery-schedules', DeliveryScheduleViewSet, basename='delivery-schedules')
router.register(r'admin/delivery-persons', DeliveryPersonAdminViewSet, basename='delivery-persons')
router.register(r'delivery/my-orders', DeliveryPersonOrderViewSet, basename='delivery-person-orders')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/assign-delivery/', AdminAssignDeliveryView.as_view(), name='admin-assign-delivery'),
    path('delivery/login/', DeliveryPersonLoginView.as_view(), name='delivery-person-login'),
    path('delivery/me/', DeliveryPersonProfileView.as_view(), name='delivery-person-profile'),
    path('delivery-slots/', CustomerDeliverySlotsView.as_view(), name='customer-delivery-slots'),
]
