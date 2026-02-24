from django.db import models
from django.utils.text import slugify
from categories.models import Category, SubCategory
from users.models import User
from ckeditor.fields import RichTextField

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = RichTextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True)
    brand = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_products')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_products')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if not self.pk or self.name != Product.objects.get(pk=self.pk).name:
            self.slug = slugify(self.name)
        if not self.pk and user:
            self.created_by = user
        if user:
            self.updated_by = user
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'product'
        indexes = [
            models.Index(fields=['category', 'subcategory']),
            models.Index(fields=['is_active']),
            models.Index(fields=['brand']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created_at']),
        ]


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    quantity = models.DecimalField(max_digits=5, decimal_places=2)
    unit = models.CharField(max_length=10, choices=[
        ('kg', 'Kilogram'), ('g', 'Gram'), ('l', 'Litre'),
        ('ml', 'Millilitre'), ('pc', 'Piece')
    ])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}{self.unit}"

    class Meta:
        db_table = 'product_variant'
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['unit']),
            models.Index(fields=['is_available']),
        ]
        unique_together = ('product', 'quantity', 'unit')


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    alt_text = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_product_images')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_product_images')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if not self.pk and user:
            self.created_by = user
        if user:
            self.updated_by = user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        db_table = 'product_image'
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['created_by']),
        ]