from django.contrib import admin
from .models import Product, ProductVariant, ProductImage


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'created_by', 'updated_by']
    readonly_fields = ['created_by', 'updated_by']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id','name', 'category', 'subcategory', 'brand', 'is_active', 'created_at']
    list_filter = ['category', 'subcategory', 'brand', 'is_active']
    search_fields = ['name', 'brand', 'description']
    inlines = [ProductVariantInline, ProductImageInline]
    readonly_fields = ['slug', 'created_by', 'updated_by', 'created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'unit', 'price', 'discounted_price', 'stock', 'is_available']
    list_filter = ['unit', 'is_available']
    search_fields = ['product__name']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text', 'created_by', 'updated_by', 'created_at']
    search_fields = ['product__name', 'alt_text']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
