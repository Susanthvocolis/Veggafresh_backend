from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AddressViewSet, AdminAddressViewSet

# User routes
user_router = DefaultRouter()
user_router.register(r'address', AddressViewSet, basename='address')

# Admin routes
admin_router = DefaultRouter()
admin_router.register(r'admin/addresses', AdminAddressViewSet, basename='admin-addresses')

urlpatterns = [
    path('', include(user_router.urls)),
    path('', include(admin_router.urls)),
]
