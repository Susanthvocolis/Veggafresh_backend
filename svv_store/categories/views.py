from rest_framework import viewsets, status
from rest_framework.response import Response

from categories.permissions import IsSuperAdminOrHasCategoryPermission
from products.models import Product
from .models import Category, SubCategory
from .serializers import CategorySerializer, SubCategorySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsSuperAdminOrHasCategoryPermission]

    def perform_create(self, serializer):
        # Pass the current user to the model's save method
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        # Only update the updated_by field when modifying
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()

        # Get related subcategories
        subcategories = category.subcategories.all()
        # Get related products (assuming a ForeignKey from Product -> SubCategory)
        related_products = Product.objects.filter(subcategory__in=subcategories)

        if related_products.exists() and request.query_params.get("confirm") != "true":
            return Response({
                "message": "This category has associated products. Deleting it will make all those products inactive.",
                "confirm_url": f"{request.build_absolute_uri()}?confirm=true"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mark related products as inactive
        related_products.update(is_active=False)

        # Now delete the category
        category.delete()

        return Response({"message": "Category deleted. Associated products have been marked as inactive."},
                        status=status.HTTP_204_NO_CONTENT)

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsSuperAdminOrHasCategoryPermission]

    def perform_create(self, serializer):
        # Pass the current user to the model's save method
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        # Only update the updated_by field when modifying
        serializer.save(updated_by=self.request.user)