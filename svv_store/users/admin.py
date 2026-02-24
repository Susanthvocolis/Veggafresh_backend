
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .form import AdminEmailMobileLoginForm, CustomUserChangeForm
from .models import User, OTP, ModulePermission


class CustomUserAdmin(UserAdmin):
    model = User
    form = CustomUserChangeForm
    list_display = ('mobile', 'email', 'role', 'is_staff', 'is_active', 'profile_complete')
    list_filter = ('role', 'is_staff', 'is_active', 'profile_complete')
    fieldsets = (
        (None, {'fields': ('mobile', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
        ('Profile Status', {'fields': ('profile_complete', 'date_of_birth', 'address')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile', 'password1', 'password2', 'role'),
        }),
    )
    search_fields = ('mobile', 'email')
    ordering = ('-date_joined',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role == User.Role.ADMIN:
            return qs.filter(role=User.Role.USER)
        return qs

    def has_add_permission(self, request):
        return request.user.role in [User.Role.SUPER_ADMIN, User.Role.ADMIN]

    def has_change_permission(self, request, obj=None):
        if obj and request.user.role == User.Role.ADMIN:
            return obj.role == User.Role.USER
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and request.user.role == User.Role.ADMIN:
            return obj.role == User.Role.USER
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if request.user.role == User.Role.ADMIN and obj.role != User.Role.USER:
            raise PermissionError("Admins can only create regular users")
        super().save_model(request, obj, form, change)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'identifier_type', 'otp', 'is_used', 'created_at', 'expired_at')
    list_filter = ('identifier_type', 'is_used')
    search_fields = ('identifier', 'otp')
    readonly_fields = ('created_at', 'expired_at')
    ordering = ('-created_at',)
@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = (
        'employee',

        # Product permissions
        'can_add_product', 'can_edit_product', 'can_delete_product',

        # Category permissions
        'can_add_category', 'can_view_category',
        'can_edit_category', 'can_delete_category',

        # Sub-category permissions
        'can_add_subcategory', 'can_view_subcategory',
        'can_edit_subcategory', 'can_delete_subcategory',

        # Order and delivery permissions
        'can_manage_orders', 'can_manage_delivery_status',

        # Payment permissions
        'can_view_payment',

        # User management permissions
        'can_view_users', 'can_update_users', 'can_delete_users',
    )

    search_fields = (
        'employee__email', 'employee__first_name', 'employee__mobile',
    )

    list_filter = (
        # Product filters
        'can_add_product', 'can_edit_product', 'can_delete_product',

        # Category filters
        'can_add_category', 'can_view_category',
        'can_edit_category', 'can_delete_category',

        # Sub-category filters
        'can_add_subcategory', 'can_view_subcategory',
        'can_edit_subcategory', 'can_delete_subcategory',

        # Order/delivery
        'can_manage_orders', 'can_manage_delivery_status',

        # Payment
        'can_view_payment',

        # User management
        'can_view_users', 'can_update_users', 'can_delete_users',
    )



# Set the custom login form for admin site
admin.site.login_form = AdminEmailMobileLoginForm
admin.site.register(User, CustomUserAdmin)
