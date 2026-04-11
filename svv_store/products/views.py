import json
import mimetypes
import os

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import viewsets, status, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.signed_url import verify_signed_token
from .models import Product, ProductVariant
from .permissions import IsSuperAdminOrHasProductPermission, ImageViewPermission
from .serializers import ProductSerializer, ProductVariantSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsSuperAdminOrHasProductPermission]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'brand', 'created_at', 'category__name', 'subcategory__name']
    ordering = ['-created_at']

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
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

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
    class CustomPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100

    def get(self, request):
        params = request.query_params

        # Build a param-aware cache key — each unique filter/page combo is cached separately
        cache_key = (
            f"products"
            f"_cat{params.get('category', '')}"
            f"_sub{params.get('subcategory', '')}"
            f"_brand{params.get('brand', '')}"
            f"_q{params.get('search', '')}"
            f"_active{params.get('is_active', 'true')}"
            f"_o{params.get('ordering', '-created_at')}"
            f"_p{params.get('page', 1)}"
            f"_ps{params.get('page_size', 10)}"
        )

        cached_data = cache.get(cache_key)
        if cached_data:
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

        # Cache the paginated response data (5 minutes)
        cache.set(cache_key, response.data, timeout=60 * 5)
        return response
