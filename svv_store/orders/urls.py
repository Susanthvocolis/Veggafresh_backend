from django.urls import path, include
from rest_framework.routers import DefaultRouter

from orders.views.analytics import SalesPerMonthView, MostSoldProductOfMonth, LeastSoldProductOfMonth, SalesReportView
from orders.views.report_export import SalesReportExportView, SecureFileDownloadView
from orders.views.user_views import MyOrdersView, MyOrderDetailView, ReorderView
from orders.views.views import AdminOrderViewSet, OrderStatusViewSet, DeliveryPersonViewSet, AdminFilterOrderViewSet, OrderStatusListView

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

    # User-facing order APIs
    path('my-orders/', MyOrdersView.as_view(), name='my-orders'),
    path('my-orders/<str:order_id>/', MyOrderDetailView.as_view(), name='my-order-detail'),
    path('my-orders/<str:order_id>/reorder/', ReorderView.as_view(), name='reorder'),

    # Order status list with messages
    path('order-statuses/', OrderStatusListView.as_view(), name='order-statuses'),
]
