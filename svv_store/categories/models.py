from django.db import models
from django.utils.text import slugify

from users.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    image = models.TextField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='created_categories')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='updated_categories')

    class Meta:
        db_table = 'category'
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        user = kwargs.pop('user', None)
        if is_new:
            self.slug = slugify(self.name)
        else:
            orig = Category.objects.get(pk=self.pk)
            if orig.name != self.name:
                self.slug = slugify(self.name)
        if is_new and user:
            self.created_by = user
        if user:
            self.updated_by = user
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE,
                                 related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    is_active = models.BooleanField(default=True)
    image = models.TextField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='created_subcategories')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='updated_subcategories')

    class Meta:
        db_table = 'sub_category'
        unique_together = ('category', 'name')
        ordering = ['name']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        user = kwargs.pop('user', None)
        if is_new:
            self.slug = slugify(self.name)
        else:
            orig = SubCategory.objects.get(pk=self.pk)
            if orig.name != self.name:
                self.slug = slugify(self.name)
        if is_new and user:
            self.created_by = user
        if user:
            self.updated_by = user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"
