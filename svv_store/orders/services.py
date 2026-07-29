from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Order, OrderStatus

# How long an order is allowed to sit in "Initiated" (payment started but
# never confirmed) before it's treated as abandoned/cancelled.
STALE_INITIATED_MINUTES = 15


def expire_stale_initiated_orders(user):
    """
    Auto-cancel unpaid orders that have been sitting in 'Initiated' status
    for too long, and release their delivery slot back to the pool.

    We're online-payment-only (no COD), so an order stuck in 'Initiated'
    only ever means: the user opened the Razorpay checkout and then closed
    it / backed out / lost connectivity before completing payment. Razorpay
    does not call our webhook in that case (no payment attempt was made),
    so nothing else ever transitions this order out of 'Initiated'.

    Rather than adding a dedicated cancel endpoint the app has to remember
    to call on dismiss, we check for staleness lazily whenever the user
    reads their orders (My Orders list / order detail) — those endpoints
    already exist and are called right after the user backs out of
    checkout and lands back in the app.
    """
    cutoff = timezone.now() - timedelta(minutes=STALE_INITIATED_MINUTES)

    stale_order_ids = list(
        Order.objects
        .filter(user=user, status__name="Initiated", created_at__lt=cutoff)
        .values_list('id', flat=True)
    )
    if not stale_order_ids:
        return

    from delivery.services import release_delivery_schedule

    cancelled_status, _ = OrderStatus.objects.get_or_create(name="Cancelled")

    for order_id in stale_order_ids:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            # Re-check inside the lock: payment may have completed via
            # /verify/ or the webhook in the meantime.
            if not order.status or order.status.name != "Initiated":
                continue
            order.status = cancelled_status
            order.save(update_fields=["status"])
            release_delivery_schedule(order.delivery_schedule_id)
