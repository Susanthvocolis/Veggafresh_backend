from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InitiatePhonePePayment, PaymentViewSet, PhonePeCallbackView, CodOrderCreateView, CodCollectView

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [
    path('', include(router.urls)),
    path('payment/create/', InitiatePhonePePayment.as_view(), name='phonepe-initiate'),
    path('payment/callback/', PhonePeCallbackView.as_view(), name='phonepe-callback'),
    path('payment/cod/create/', CodOrderCreateView.as_view(), name='cod-create'),
    path('payment/cod/<str:order_id>/collect/', CodCollectView.as_view(), name='cod-collect'),
]
