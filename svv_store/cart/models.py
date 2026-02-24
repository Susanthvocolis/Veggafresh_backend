# Create your models here.
from django.db import models
from products.models import ProductVariant
from users.models import User
from decimal import Decimal
import os

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    handling_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.email}"

    def calculate_totals(self):
        if not self.items.exists():
            self.total_amount = Decimal('0.00')
            self.taxes = Decimal('0.00')
            self.handling_charges = Decimal('0.00')
            self.delivery_charges = Decimal('0.00')
            self.final_amount = Decimal('0.00')
        else:
            subtotal = sum(
                (
                        (item.product_variant.discounted_price
                         if item.product_variant.discounted_price
                            and item.product_variant.discounted_price != Decimal('0')
                         else item.product_variant.price
                         ) * item.quantity
                )
                for item in self.items.all()
            )
            taxes = subtotal * Decimal(os.getenv("TAX_PERCENT", 0.18))
            handling = Decimal(os.getenv("HANDLING_CHARGE", 30))
            delivery = Decimal(os.getenv("DELIVERY_CHARGE", 50))
            final = subtotal + taxes + handling + delivery

            self.total_amount = subtotal
            self.taxes = taxes
            self.handling_charges = handling
            self.delivery_charges = delivery
            self.final_amount = final

        self.save()

    class Meta:
        db_table = 'cart'
        indexes = [
            models.Index(fields=['user']),
        ]

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product_variant')
        db_table = 'cart_item'
        indexes = [
            models.Index(fields=['cart']),
            models.Index(fields=['product_variant']),
        ]


    def __str__(self):
        return f"{self.product_variant} x {self.quantity}"