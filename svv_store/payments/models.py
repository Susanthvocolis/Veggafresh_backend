from django.db import models
from orders.models import Order
from users.models import User

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    PAYMENT_GATEWAY_CHOICES = [
        ('phonepe', 'PhonePe'),
        ('razorpay', 'Razorpay'),
        ('cod', 'COD'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Generic fields
    payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_gateway = models.CharField(
        max_length=20, choices=PAYMENT_GATEWAY_CHOICES, default='cod'
    )

    # PhonePe-specific fields (existing — do not modify)
    phonepe_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    phonepe_response = models.JSONField(null=True, blank=True)

    # Razorpay-specific fields (new)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=512, blank=True, null=True)
    razorpay_response = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.payment_id} - {self.status}"

    class Meta:
        db_table = 'payment'
