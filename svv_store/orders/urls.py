from django.urls import path, include
from rest_framework.routers import DefaultRouter

from orders.views.analytics import SalesPerMonthView, MostSoldProductOfMonth, LeastSoldProductOfMonth, SalesReportView
from orders.views.report_export import SalesReportExportView, SecureFileDownloadView
from orders.views.views import AdminOrderViewSet, OrderStatusViewSet, DeliveryPersonViewSet, AdminFilterOrderViewSet

router = DefaultRouter()
  # or customize

router.register('delivery-persons', DeliveryPersonViewSet)
router.register(r'orders', AdminOrderViewSet, basename='admin-orders')
router.register(r'orders-filters', AdminFilterOrderViewSet, basename='admin-filter-orders')
router.register('order-status', OrderStatusViewSet, basename='order-status')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/sales-per-month/', SalesPerMonthView.as_view()),
    path('analytics/most-sold-product/', MostSoldProductOfMonth.as_view()),
    path('analytics/least-sold-product/', LeastSoldProductOfMonth.as_view()),
    path('analysis/sales-report/', SalesReportView.as_view(), name='sales-report'),
    path('generate-sales-report/', SalesReportExportView.as_view(), name='generate_sales_report'),

]
