from django.db import models
from users.models import User

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    pincode = models.CharField(max_length=10)
    address_line1 = models.TextField()
    address_line2 = models.TextField(blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)   # e.g., 12.971598
    longitude = models.DecimalField(max_digits=9, decimal_places=6)  # e.g., 77.594566
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} - {self.city}"

    class Meta:
        db_table = 'address'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['pincode']),
            models.Index(fields=['city']),
        ]
