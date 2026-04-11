from django.db import models
from users.models import User
from products.models import ProductVariant
from django.utils import timezone

class OrderStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    class Meta:
        db_table = 'order_status'
        indexes = [
            models.Index(fields=['name'])  # Index on the 'name' field for faster lookups
        ]
class DeliveryPerson(models.Model):
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20,unique=True)

    def __str__(self):
        return f"{self.name} ({self.mobile})"

    class Meta:
        db_table = 'delivery_person'
        indexes = [
            models.Index(fields=['mobile'])  # Index on the 'mobile' field for fast lookups
        ]
class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('online', 'Online'),
        ('cod', 'Cash on Delivery'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.ForeignKey(OrderStatus, on_delete=models.SET_NULL, null=True)
    address = models.ForeignKey('address.Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='online')
    tracking_link = models.URLField(blank=True, null=True)

    delivery_person = models.ForeignKey(
        'DeliveryPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(max_length=20, unique=True, blank=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    handling_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if not self.order_id:
            today = timezone.now().date()
            prefix = today.strftime('%y%m%d')  # e.g., 250413
            count_today = Order.objects.filter(created_at__date=today).count() + 1
            if count_today < 100:
                suffix = str(count_today).zfill(3)  # Pad to 3 digits (e.g., 001, 099)
            else:
                suffix = str(count_today)  # No padding if >= 100

            self.order_id = f"{prefix}{suffix}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_id} - {self.user.email if self.user else 'Unknown'}"

    class Meta:
        db_table = 'order'
        indexes = [
            models.Index(fields=['user']),  # Index on 'user' for fast user-based lookups
            models.Index(fields=['status']),  # Index on 'status' for filtering orders by status
            models.Index(fields=['created_at']),  # Index on 'created_at' for sorting by date
            models.Index(fields=['order_id']),  # Index on 'order_id' for fast lookups
        ]
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.product_variant} x {self.quantity}"

    class Meta:
        db_table = 'order_item'
        indexes = [
            models.Index(fields=['order']),  # Index on 'order' to quickly fetch items for an order
            models.Index(fields=['product_variant']),  # Index on 'product_variant' for fast lookups
        ]