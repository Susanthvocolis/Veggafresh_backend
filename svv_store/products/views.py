import json
import mimetypes
import os

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import filters, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.signed_url import verify_signed_token
from .models import Product, ProductVariant
from .permissions import ImageViewPermission, IsSuperAdminOrHasProductPermission
from .serializers import ProductSerializer, ProductVariantSerializer

PRODUCT_CACHE_TTL = 60 * 5
PRODUCT_CACHE_VERSION_KEY = "products_api_cache_version"


def get_product_cache_version():
    version = cache.get(PRODUCT_CACHE_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(PRODUCT_CACHE_VERSION_KEY, version, timeout=None)
    return version


def bump_product_cache_version():
    try:
        cache.incr(PRODUCT_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(PRODUCT_CACHE_VERSION_KEY, 2, timeout=None)


def build_product_cache_key(prefix, **parts):
    version = get_product_cache_version()
    normalized_parts = [f"{key}:{parts[key]}" for key in sorted(parts)]
    return f"{prefix}:v{version}:" + "|".join(normalized_parts)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsSuperAdminOrHasProductPermission]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['name', 'brand', 'slug', 'category__name', 'subcategory__name']
    ordering_fields = ['name', 'brand', 'created_at', 'category__name', 'subcategory__name']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        is_active = self.request.query_params.get('is_active')
        queryset = Product.objects.select_related(
            'category', 'subcategory', 'created_by', 'updated_by'
        ).prefetch_related(
            'variants', 'images'
        ).order_by('-created_at')

        if is_active is None:
            queryset = queryset.filter(is_active=True)
        elif is_active.lower() in ['true', 'false']:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def list(self, request, *args, **kwargs):
        cache_key = build_product_cache_key(
            "product_list",
            page=request.query_params.get('page', ''),
            page_no=request.query_params.get('page_no', ''),
            page_size=request.query_params.get('page_size', ''),
            query_params=request.query_params.urlencode(),
        )
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=PRODUCT_CACHE_TTL)
        return response

    def retrieve(self, request, *args, **kwargs):
        cache_key = build_product_cache_key(
            "product_detail",
            product_id=kwargs.get('pk'),
            query_params=request.query_params.urlencode(),
        )
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=PRODUCT_CACHE_TTL)
        return response

    def create(self, request, *args, **kwargs):
        processed_data = {}

        for key in request.data:
            if not key.startswith('variants') and not key.startswith('image'):
                processed_data[key] = request.data[key]

        if 'variants' in request.data:
            try:
                variants_str = request.data['variants'].strip()
                processed_data['variants'] = json.loads(variants_str)
            except json.JSONDecodeError as e:
                return Response(
                    {"message": "Failed", "data": {"variants": [f"Invalid JSON format: {str(e)}"]}},
                    status=status.HTTP_400_BAD_REQUEST
                )

        images = []
        uploaded_images = request.FILES.getlist('images')
        alt_texts = request.data.getlist('alt_text')

        for idx, img in enumerate(uploaded_images):
            alt_text = alt_texts[idx] if idx < len(alt_texts) else ''
            images.append({'image': img, 'alt_text': alt_text})

        processed_data['images'] = images

        serializer = self.get_serializer(data=processed_data)

        if not serializer.is_valid():
            return Response(
                {"message": "Failed", "data": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_create(serializer)
        bump_product_cache_version()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        processed_data = {}

        for key in request.data:
            if not key.startswith('variants') and not key.startswith('image'):
                processed_data[key] = request.data[key]

        if 'variants' in request.data:
            try:
                variants_str = request.data['variants'].strip()
                processed_data['variants'] = json.loads(variants_str)
            except json.JSONDecodeError as e:
                return Response(
                    {"message": "Failed", "data": {"variants": [f"Invalid JSON format: {str(e)}"]}},
                    status=status.HTTP_400_BAD_REQUEST
                )

        uploaded_images = request.FILES.getlist('images')
        alt_texts = request.data.getlist('alt_text')

        if uploaded_images:
            instance.images.all().delete()

            images = []
            for idx, img in enumerate(uploaded_images):
                alt_text = alt_texts[idx] if idx < len(alt_texts) else ''
                images.append({'image': img, 'alt_text': alt_text})

            processed_data['images'] = images

        serializer = self.get_serializer(instance=instance, data=processed_data, partial=True)

        if not serializer.is_valid():
            return Response(
                {"message": "Failed", "data": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_update(serializer)
        bump_product_cache_version()
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        bump_product_cache_version()
        return response

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsSuperAdminOrHasProductPermission]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['product__name', 'price', 'discounted_price']
    ordering = ['id']


class SecureMediaView(APIView):
    permission_classes = [ImageViewPermission]

    def get(self, request, token):
        try:
            file_path = verify_signed_token(token)
        except Exception:
            raise Http404("Invalid or expired link.")

        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        if not os.path.exists(full_path):
            raise Http404("File not found.")

        content_type, _ = mimetypes.guess_type(full_path)
        return FileResponse(open(full_path, 'rb'), content_type=content_type)


class UserProductAPIView(APIView):
    permission_classes = [AllowAny]

    class CustomPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100

    def get(self, request):
        params = request.query_params

        cache_key = build_product_cache_key(
            "user_product_list",
            category=params.get('category', ''),
            subcategory=params.get('subcategory', ''),
            brand=params.get('brand', ''),
            search=params.get('search', ''),
            is_active=params.get('is_active', 'true'),
            ordering=params.get('ordering', '-created_at'),
            page=params.get('page', 1),
            page_size=params.get('page_size', 10),
        )

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        ordering = params.get('ordering', '-created_at')
        allowed_orderings = ['name', '-name', 'created_at', '-created_at']
        if ordering not in allowed_orderings:
            ordering = '-created_at'

        queryset = Product.objects.select_related(
            'category', 'subcategory', 'created_by', 'updated_by'
        ).prefetch_related(
            'variants', 'images'
        ).order_by(ordering)

        is_active = params.get('is_active')
        if is_active is None:
            queryset = queryset.filter(is_active=True)
        elif is_active.lower() in ['true', 'false']:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        category_id = params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        subcategory_id = params.get('subcategory')
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)

        brand = params.get('brand')
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        search_query = params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(slug__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(subcategory__name__icontains=search_query)
            )

        paginator = self.CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductSerializer(page, many=True, context={'request': request})
        response = paginator.get_paginated_response(serializer.data)

        cache.set(cache_key, response.data, timeout=PRODUCT_CACHE_TTL)
        return response
