from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ProductVariantViewSet, SecureMediaView, UserProductAPIView

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'variants', ProductVariantViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('secure-media/<str:token>/', SecureMediaView.as_view(), name='secure-media'),
    path('user-products/', UserProductAPIView.as_view(), name='secure-media'),

]
