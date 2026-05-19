from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import BannerViewSet

router = DefaultRouter()
router.register(r'banners', BannerViewSet, basename='banner')

urlpatterns = [
    path('', include(router.urls)),
]
