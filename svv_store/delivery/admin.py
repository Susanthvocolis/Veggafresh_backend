from django.contrib import admin

from .models import DeliverySchedule, DeliverySlot


@admin.register(DeliverySlot)
class DeliverySlotAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('sort_order', 'start_time')


@admin.register(DeliverySchedule)
class DeliveryScheduleAdmin(admin.ModelAdmin):
    list_display = ('delivery_date', 'slot', 'max_orders', 'booked_orders', 'is_active', 'is_blocked')
    list_filter = ('delivery_date', 'is_active', 'is_blocked', 'slot')
    search_fields = ('slot__name',)
    ordering = ('delivery_date', 'slot__sort_order', 'slot__start_time')
