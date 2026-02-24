from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'user', 'order', 'amount', 'status', 'payment_date')
    list_filter = ('status', 'payment_date')
    search_fields = ('payment_id', 'order__id', 'user__email')
    ordering = ('-payment_date',)
