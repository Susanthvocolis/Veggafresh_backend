from django.urls import path
from .views import InitiatePhonePePayment, PaymentViewSet, PhonePeCallbackView
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [
    path('', include(router.urls)),
    path('payment/create/', InitiatePhonePePayment.as_view(), name='phonepe-initiate'),
    path('payment/callback/', PhonePeCallbackView.as_view(), name='phonepe-callback'),

]
