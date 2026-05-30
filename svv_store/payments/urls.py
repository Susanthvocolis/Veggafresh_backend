from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InitiatePhonePePayment,
    PaymentViewSet,
    PhonePeCallbackView,
    CodOrderCreateView,
    CodCollectView,
    InvoicePdfDownloadView,
)
from .razorpay_views import (
    InitiateRazorpayPayment,
    InitiateRazorpayMobilePayment,
    RazorpayPaymentInvoiceView,
    RazorpayPaymentFailedRedirectView,
    RazorpayPaymentSuccessRedirectView,
    RazorpayPaymentVerifyView,
    RazorpayWebhookView,
)

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
    path('payment/<str:order_id>/invoice/download/', InvoicePdfDownloadView.as_view(), name='invoice-pdf-download'),

    # ---- Razorpay (new) ----
    path('payment/razorpay/create/', InitiateRazorpayPayment.as_view(), name='razorpay-create'),
    path('payment/razorpay/mobile/create/', InitiateRazorpayMobilePayment.as_view(), name='razorpay-mobile-create'),
    path('payment/razorpay/mobile/verify/', RazorpayPaymentVerifyView.as_view(), name='razorpay-mobile-verify'),
    path('payment/razorpay/success/', RazorpayPaymentSuccessRedirectView.as_view(), name='razorpay-success'),
    path('payment/razorpay/failed/', RazorpayPaymentFailedRedirectView.as_view(), name='razorpay-failed'),
    path('payment/razorpay/<str:order_id>/invoice/', RazorpayPaymentInvoiceView.as_view(), name='razorpay-invoice'),
    path('payment/razorpay/verify/', RazorpayPaymentVerifyView.as_view(), name='razorpay-verify'),
    path('payment/razorpay/webhook/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
]
