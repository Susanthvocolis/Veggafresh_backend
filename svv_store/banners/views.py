from django.db import models as django_models
from django.utils import timezone
from rest_framework import viewsets, filters, generics
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import Banner
from .permissions import IsSuperAdminOrHasBannerPermission
from .serializers import BannerSerializer, PublicBannerSerializer


def active_schedule_filter(queryset):
    """Keep only banners that are currently live based on schedule dates."""
    now = timezone.now()
    return queryset.filter(
        is_active=True,
    ).filter(
        django_models.Q(start_date__isnull=True) | django_models.Q(start_date__lte=now)
    ).filter(
        django_models.Q(end_date__isnull=True) | django_models.Q(end_date__gte=now)
    )


class BannerViewSet(viewsets.ModelViewSet):
    """
    CRUD for banners (hero, offer strip, category, app-promo).

    Query params:
      ?banner_type=hero|offer|category|app_promo
      ?is_active=true|false
      ?active_only=true  → only return currently live banners
      ?search=<text>     → search title / subtitle
    """
    serializer_class = BannerSerializer
    permission_classes = [IsSuperAdminOrHasBannerPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter, DjangoFilterBackend]
    ordering_fields = ['position', 'created_at', 'banner_type']
    search_fields = ['title', 'subtitle']
    filterset_fields = ['banner_type', 'is_active']
    ordering = ['position', '-created_at']

    def get_queryset(self):
        qs = Banner.objects.all()
        if self.request.query_params.get('active_only') == 'true':
            qs = active_schedule_filter(qs)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class UserBannerAPIView(generics.ListAPIView):
    """
    Public storefront banner feed.

    Query params:
      ?banner_type=hero|offer|category|app_promo
    """
    serializer_class = PublicBannerSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = active_schedule_filter(Banner.objects.all())
        banner_type = self.request.query_params.get('banner_type')
        if banner_type:
            qs = qs.filter(banner_type=banner_type)
        return qs.order_by('position', '-created_at')
