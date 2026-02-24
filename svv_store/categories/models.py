import time

from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify

from users.models import User

def category_image_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    timestamp = int(time.time())
    unique_filename = f"{instance.slug}-{timestamp}.{ext}"
    if instance.pk:
        return f"categories/{instance.pk}/{unique_filename}"
    return f"categories/temp/{unique_filename}"

def subcategory_image_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    timestamp = int(time.time())
    unique_filename = f"{instance.slug}-{timestamp}.{ext}"
    if instance.pk:
        return f"subcategories/{instance.pk}/{unique_filename}"
    return f"subcategories/temp/{unique_filename}"
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to=category_image_upload_path, null=True, blank=True)

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
        original_image = self.image if is_new else None  # Only move image for new records
        # Slug logic
        if is_new:
            self.slug = slugify(self.name)
        else:
            orig = Category.objects.get(pk=self.pk)
            if orig.name != self.name:
                self.slug = slugify(self.name)
        # Audit fields
        if is_new and user:
            self.created_by = user
        if user:  # On any update
            self.updated_by = user

        super().save(*args, **kwargs)

        # Handle image renaming after save (only for new records)
        if is_new and original_image:
            ext = original_image.name.split('.')[-1]
            timestamp = int(time.time())
            new_path = f"categories/{self.pk}/{timestamp}.{ext}"

            # Move file pointer back to the beginning
            original_image.open()
            file_data = original_image.read()
            original_image.close()

            self.image.save(new_path, ContentFile(file_data), save=False)
            super().save(update_fields=["image"])
    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE,
                                 related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to=subcategory_image_upload_path, null=True, blank=True)

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
        original_image = self.image if is_new else None  # Only move image for new records
        # Slug logic
        if is_new:
            self.slug = slugify(self.name)
        else:
            orig = SubCategory.objects.get(pk=self.pk)
            if orig.name != self.name:
                self.slug = slugify(self.name)
        # Audit fields
        if is_new and user:
            self.created_by = user
        if user:
            self.updated_by = user

        super().save(*args, **kwargs)

        # Handle image renaming after save (only for new records)
        if is_new and original_image:
            ext = original_image.name.split('.')[-1]
            timestamp = int(time.time())
            new_path = f"subcategories/{self.pk}/{timestamp}.{ext}"

            # Move file pointer back to the beginning
            original_image.open()
            file_data = original_image.read()
            original_image.close()

            self.image.save(new_path, ContentFile(file_data), save=False)
            super().save(update_fields=["image"])

    def __str__(self):
        return f"{self.category.name} - {self.name}"