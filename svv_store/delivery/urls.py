from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomerDeliverySlotsView, DeliveryScheduleViewSet, DeliverySlotViewSet


router = DefaultRouter()
router.register(r'admin/delivery-slots', DeliverySlotViewSet, basename='delivery-slots')
router.register(r'admin/delivery-schedules', DeliveryScheduleViewSet, basename='delivery-schedules')

urlpatterns = [
    path('', include(router.urls)),
    path('delivery-slots/', CustomerDeliverySlotsView.as_view(), name='customer-delivery-slots'),
]
