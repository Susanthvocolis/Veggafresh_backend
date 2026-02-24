from django.db.models import Q
from rest_framework import viewsets
from django.core.cache import cache
from utils.signed_url import verify_signed_token
from .models import Product, ProductVariant
from .permissions import IsSuperAdminOrHasProductPermission, ImageViewPermission
from .serializers import ProductSerializer, ProductVariantSerializer

import json
from rest_framework import viewsets, status
from .models import Product
from .serializers import ProductSerializer
import mimetypes
from django.http import FileResponse, Http404
from django.conf import settings
import os
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsSuperAdminOrHasProductPermission]

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
        # Create a new mutable dictionary for our data
        processed_data = {}

        # Copy over all the simple fields
        for key in request.data:
            if not key.startswith('variants') and not key.startswith('image'):
                processed_data[key] = request.data[key]

        # Process variants - parse from JSON string
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
        alt_texts = request.data.getlist('alt_text')  # Optional alt texts

        for idx, img in enumerate(uploaded_images):
            alt_text = alt_texts[idx] if idx < len(alt_texts) else ''
            images.append({'image': img, 'alt_text': alt_text})

        processed_data['images'] = images

        # Create serializer with our processed data
        serializer = self.get_serializer(data=processed_data)

        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
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

        # Copy over all the simple fields
        for key in request.data:
            if not key.startswith('variants') and not key.startswith('image'):
                processed_data[key] = request.data[key]

        # Process variants - parse from JSON string
        if 'variants' in request.data:
            try:
                variants_str = request.data['variants'].strip()
                processed_data['variants'] = json.loads(variants_str)
            except json.JSONDecodeError as e:
                return Response(
                    {"message": "Failed", "data": {"variants": [f"Invalid JSON format: {str(e)}"]}},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Process images
        # Process image list
        uploaded_images = request.FILES.getlist('images')
        alt_texts = request.data.getlist('alt_text')

        if uploaded_images:
            # Delete existing images if new ones are uploaded
            instance.images.all().delete()

            images = []
            for idx, img in enumerate(uploaded_images):
                alt_text = alt_texts[idx] if idx < len(alt_texts) else ''
                images.append({'image': img, 'alt_text': alt_text})

            processed_data['images'] = images

            if images:
                # Delete previous images
                instance.images.all().delete()
                processed_data['images'] = images

        # Create serializer with our processed data
        serializer = self.get_serializer(instance=instance, data=processed_data, partial=True)

        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
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


class SecureMediaView(APIView):
    permission_classes = [ImageViewPermission]  # Or custom permissions
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
        print("hello")
        cache_key = 'product_list_cache'  # Unique cache key for product list
        cached_data = cache.get(cache_key)
        # cache.delete('product_list_cache')
        if cached_data:
            print((cached_data,"HELO"))
            return Response(cached_data)
        queryset = Product.objects.select_related(
            'category', 'subcategory', 'created_by', 'updated_by'
        ).prefetch_related(
            'variants', 'images'
        ).order_by('-created_at')

        params = request.query_params

        # Filter by is_active
        is_active = params.get('is_active')
        if is_active is None:
            queryset = queryset.filter(is_active=True)
        elif is_active.lower() in ['true', 'false']:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by category ID
        category_id = params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by subcategory ID
        subcategory_id = params.get('subcategory')
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)

        # Filter by brand
        brand = params.get('brand')
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        # Search by name or slug
        search_query = params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(slug__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(subcategory__name__icontains=search_query)
            )

        # Pagination
        paginator = self.CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ProductSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        # No pagination: serialize all results
        serializer = ProductSerializer(queryset, many=True, context={'request': request})
        cache.set(cache_key, serializer.data, timeout=60*5)  # Cache for 5 minutes
        # Get the cached value
        value = cache.get(cache_key)
        print(value,"heleeelo")
        return Response(serializer.data)