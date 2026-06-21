from django.core.exceptions import ValidationError
from django.db import models


class DeliverySlot(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Slot start_time must be before end_time.")

    def __str__(self):
        return f"{self.name} ({self.start_time:%H:%M}-{self.end_time:%H:%M})"

    class Meta:
        db_table = 'delivery_slot'
        ordering = ['sort_order', 'start_time', 'name']
        indexes = [
            models.Index(fields=['is_active', 'sort_order'], name='delivery_sl_is_acti_7cc41d_idx'),
            models.Index(fields=['start_time', 'end_time'], name='delivery_sl_start_t_3e7b1a_idx'),
        ]


class DeliverySchedule(models.Model):
    delivery_date = models.DateField()
    slot = models.ForeignKey(DeliverySlot, on_delete=models.PROTECT, related_name='schedules')
    max_orders = models.PositiveIntegerField(default=0)
    booked_orders = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def available_capacity(self):
        return max(self.max_orders - self.booked_orders, 0)

    @property
    def is_available(self):
        return (
            self.is_active
            and not self.is_blocked
            and self.slot.is_active
            and self.booked_orders < self.max_orders
        )

    def clean(self):
        if self.booked_orders > self.max_orders:
            raise ValidationError("booked_orders cannot be greater than max_orders.")

    def __str__(self):
        return f"{self.delivery_date} - {self.slot.name}"

    class Meta:
        db_table = 'delivery_schedule'
        ordering = ['delivery_date', 'slot__sort_order', 'slot__start_time']
        constraints = [
            models.UniqueConstraint(fields=['delivery_date', 'slot'], name='uniq_delivery_schedule_date_slot'),
            models.CheckConstraint(
                check=models.Q(booked_orders__lte=models.F('max_orders')),
                name='delivery_schedule_booked_lte_max',
            ),
        ]
        indexes = [
            models.Index(fields=['delivery_date', 'is_active', 'is_blocked'], name='delivery_sc_deliver_403dc2_idx'),
            models.Index(fields=['slot', 'delivery_date'], name='delivery_sc_slot_id_8675e0_idx'),
        ]
