from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InitiatePhonePePayment, PaymentViewSet, PhonePeCallbackView, CodOrderCreateView, CodCollectView
from .razorpay_views import InitiateRazorpayPayment, RazorpayPaymentVerifyView, RazorpayWebhookView

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [
    path('', include(router.urls)),

    # ---- PhonePe (existing — do not touch) ----
    path('payment/create/', InitiatePhonePePayment.as_view(), name='phonepe-initiate'),
    path('payment/callback/', PhonePeCallbackView.as_view(), name='phonepe-callback'),

    # ---- COD (existing — do not touch) ----
    path('payment/cod/create/', CodOrderCreateView.as_view(), name='cod-create'),
    path('payment/cod/<str:order_id>/collect/', CodCollectView.as_view(), name='cod-collect'),

    # ---- Razorpay (new) ----
    path('payment/razorpay/create/', InitiateRazorpayPayment.as_view(), name='razorpay-create'),
    path('payment/razorpay/verify/', RazorpayPaymentVerifyView.as_view(), name='razorpay-verify'),
    path('payment/razorpay/webhook/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
]
