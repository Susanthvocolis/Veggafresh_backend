from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from users.managers import CustomUserManager
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', _('Super Admin')
        ADMIN = 'ADMIN', _('Admin')
        USER = 'USER', _('User')

    objects = CustomUserManager()
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)
    first_name = models.CharField(max_length=150, unique=False, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    mobile = models.CharField(max_length=15, unique=True,blank=True, null=True)
    email = models.EmailField(_('email address'), unique=True,blank=True, null=True)  # Add unique constraint
    is_mobile_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    profile_complete = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    USERNAME_FIELD = 'mobile'  # Keep mobile as USERNAME_FIELD for admin compatibility
    REQUIRED_FIELDS = ['username', 'email']

    def __str__(self):
        return f"{self.email}"

    class Meta:
        db_table = 'user'


class OTP(models.Model):
    # Change mobile field to identifier (can be email or mobile)
    identifier = models.CharField(max_length=255)  # Stores email or mobile
    identifier_type = models.CharField(max_length=10, choices=[('mobile', 'Mobile'), ('email', 'Email')])
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    message_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expired_at:
            self.expired_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expired_at

    class Meta:
        db_table = 'otp'
        indexes = [
            models.Index(fields=['identifier']),
            models.Index(fields=['identifier', 'is_used', 'expired_at']),
        ]
        ordering = ['-created_at']

class ModulePermission(models.Model):
    employee = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permissions')

    # Product permissions
    can_add_product = models.BooleanField(default=False)
    can_edit_product = models.BooleanField(default=False)
    can_delete_product = models.BooleanField(default=False)
    can_view_product = models.BooleanField(default=False)

    # Category permissions
    can_add_category = models.BooleanField(default=False)
    can_view_category = models.BooleanField(default=False)
    can_edit_category = models.BooleanField(default=False)
    can_delete_category = models.BooleanField(default=False)

    # Sub-Category permissions
    can_add_subcategory = models.BooleanField(default=False)
    can_view_subcategory = models.BooleanField(default=False)
    can_edit_subcategory = models.BooleanField(default=False)
    can_delete_subcategory = models.BooleanField(default=False)

    # Order permissions
    can_manage_orders = models.BooleanField(default=False)
    can_manage_delivery_status = models.BooleanField(default=False)

    # Payment
    can_view_payment = models.BooleanField(default=False)

    # End users view
    can_view_users = models.BooleanField(default=False)
    can_update_users = models.BooleanField(default=False)
    can_delete_users = models.BooleanField(default=False)

    class Meta:
        db_table = 'module_permission'
