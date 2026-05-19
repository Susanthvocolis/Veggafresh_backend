from django import forms
from django.contrib import admin
from django.utils.html import format_html
import base64

from .models import Banner


class BannerAdminForm(forms.ModelForm):
    image_file = forms.ImageField(
        required=False, 
        help_text="Upload an image. It will be converted to Base64 automatically and saved to the database."
    )
    mobile_image_file = forms.ImageField(
        required=False, 
        help_text="Upload a mobile image. It will be converted to Base64 automatically."
    )

    class Meta:
        model = Banner
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make the text fields optional in the form so validation passes
        # if the user uploads a file instead.
        if 'image' in self.fields:
            self.fields['image'].required = False

    def clean(self):
        cleaned_data = super().clean()

        # Handle Desktop Image Upload
        image_file = cleaned_data.get('image_file')
        if image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            mime_type = getattr(image_file, 'content_type', 'image/jpeg')
            cleaned_data['image'] = f"data:{mime_type};base64,{encoded}"
        elif not cleaned_data.get('image'):
            # If no file uploaded and text field is also empty, throw error
            self.add_error('image_file', 'An image is required (either upload or paste base64).')

        # Handle Mobile Image Upload
        mobile_image_file = cleaned_data.get('mobile_image_file')
        if mobile_image_file:
            encoded = base64.b64encode(mobile_image_file.read()).decode('utf-8')
            mime_type = getattr(mobile_image_file, 'content_type', 'image/jpeg')
            cleaned_data['mobile_image'] = f"data:{mime_type};base64,{encoded}"

        return cleaned_data


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerAdminForm
    
    list_display  = ['title', 'banner_type', 'position', 'is_active', 'start_date', 'end_date', 'created_at']
    list_filter   = ['banner_type', 'is_active']
    search_fields = ['title', 'subtitle']
    ordering      = ['position', '-created_at']
    
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at', 'image_preview', 'mobile_image_preview']
    
    fieldsets = (
        ('General Information', {
            'fields': ('title', 'subtitle', 'banner_type', 'link_url', 'position', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date')
        }),
        ('Desktop Image', {
            'fields': ('image_file', 'image_preview', 'image'),
            'description': 'Upload a file OR paste an existing base64/URL string.'
        }),
        ('Mobile Image', {
            'fields': ('mobile_image_file', 'mobile_image_preview', 'mobile_image'),
            'description': 'Optional. Upload a file OR paste an existing base64/URL string.'
        }),
        ('Audit Info', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 150px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" />', obj.image)
        return "No image yet"
    image_preview.short_description = 'Current Desktop Image'

    def mobile_image_preview(self, obj):
        if obj.mobile_image:
            return format_html('<img src="{}" style="max-height: 150px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);" />', obj.mobile_image)
        return "No mobile image yet"
    mobile_image_preview.short_description = 'Current Mobile Image'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
