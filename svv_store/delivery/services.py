from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils.dateparse import parse_date
from django.utils import timezone
from rest_framework import serializers

from .models import DeliveryPerson, DeliverySchedule, DeliverySlot


def get_available_delivery_options(days=30):
    now = timezone.localtime()
    today = now.date()
    current_time = now.time()
    end_date = today + timedelta(days=days - 1)

    slots = list(DeliverySlot.objects.filter(is_active=True).order_by('sort_order', 'start_time', 'name'))
    schedules = {
        (schedule.delivery_date, schedule.slot_id): schedule
        for schedule in DeliverySchedule.objects.select_related('slot').filter(
            delivery_date__gte=today,
            delivery_date__lte=end_date,
            slot__is_active=True,
        )
    }

    options = []
    for offset in range(days):
        delivery_date = today + timedelta(days=offset)
        for slot in slots:
            if delivery_date == today and slot.start_time <= current_time:
                continue

            schedule = schedules.get((delivery_date, slot.id))
            if schedule:
                if not schedule.is_available:
                    continue
                available_capacity = schedule.available_capacity
                schedule_id = schedule.id
            else:
                available_capacity = settings.DEFAULT_DELIVERY_SLOT_CAPACITY
                schedule_id = None

            options.append({
                'date': delivery_date,
                'slot_id': slot.id,
                'schedule_id': schedule_id,
                'slot_name': slot.name,
                'start_time': slot.start_time,
                'end_time': slot.end_time,
                'available_capacity': available_capacity,
            })

    return options


def get_available_schedules(days=30):
    now = timezone.localtime()
    today = now.date()
    current_time = now.time()

    queryset = (
        DeliverySchedule.objects
        .select_related('slot')
        .filter(
            delivery_date__gte=today,
            is_active=True,
            is_blocked=False,
            slot__is_active=True,
            booked_orders__lt=F('max_orders'),
        )
        .order_by('delivery_date', 'slot__sort_order', 'slot__start_time')
    )
    if days:
        queryset = queryset.filter(delivery_date__lte=today + timedelta(days=days - 1))

    return [
        schedule for schedule in queryset
        if schedule.delivery_date > today or schedule.slot.start_time > current_time
    ]


def _parse_delivery_date(delivery_date):
    if not delivery_date:
        raise serializers.ValidationError({"delivery_date": "This field is required."})
    if hasattr(delivery_date, "isoformat"):
        return delivery_date

    parsed_date = parse_date(str(delivery_date))
    if not parsed_date:
        raise serializers.ValidationError({"delivery_date": "Use YYYY-MM-DD format."})
    return parsed_date


def _get_or_create_schedule(slot, delivery_date):
    defaults = {
        'max_orders': settings.DEFAULT_DELIVERY_SLOT_CAPACITY,
        'booked_orders': 0,
        'is_active': True,
        'is_blocked': False,
    }
    try:
        schedule, _ = DeliverySchedule.objects.get_or_create(
            delivery_date=delivery_date,
            slot=slot,
            defaults=defaults,
        )
    except IntegrityError:
        schedule = DeliverySchedule.objects.get(delivery_date=delivery_date, slot=slot)

    return (
        DeliverySchedule.objects
        .select_for_update()
        .select_related('slot')
        .get(id=schedule.id)
    )


def reserve_delivery_slot(delivery_slot_id, delivery_date):
    if not delivery_slot_id:
        raise serializers.ValidationError({"delivery_slot_id": "This field is required."})

    delivery_date = _parse_delivery_date(delivery_date)

    try:
        slot = DeliverySlot.objects.get(id=delivery_slot_id, is_active=True)
    except DeliverySlot.DoesNotExist:
        raise serializers.ValidationError({"delivery_slot_id": "Invalid or inactive delivery slot."})

    schedule = _get_or_create_schedule(slot, delivery_date)

    now = timezone.localtime()
    if schedule.delivery_date < now.date():
        raise serializers.ValidationError({"delivery_date": "Delivery date has already passed."})
    if schedule.delivery_date == now.date() and schedule.slot.start_time <= now.time():
        raise serializers.ValidationError({"delivery_slot_id": "Delivery slot is no longer available."})
    if not schedule.is_available:
        raise serializers.ValidationError({"delivery_slot_id": "Delivery slot is not available for this date."})

    schedule.booked_orders += 1
    schedule.save(update_fields=['booked_orders', 'updated_at'])

    return schedule, {
        'delivery_schedule': schedule,
        'delivery_date': schedule.delivery_date,
        'delivery_slot_name': schedule.slot.name,
        'slot_start_time': schedule.slot.start_time,
        'slot_end_time': schedule.slot.end_time,
    }


def release_delivery_schedule(schedule_id):
    if not schedule_id:
        return

    try:
        schedule = DeliverySchedule.objects.select_for_update().get(id=schedule_id)
    except DeliverySchedule.DoesNotExist:
        return

    if schedule.booked_orders > 0:
        schedule.booked_orders -= 1
        schedule.save(update_fields=['booked_orders', 'updated_at'])


def _get_order_for_assignment(order_identifier):
    from orders.models import Order

    order_id = str(order_identifier).strip()
    queryset = Order.objects.select_for_update()

    order = queryset.filter(order_id=order_id).first()
    if order:
        return order

    if order_id.isdigit():
        order = queryset.filter(pk=int(order_id)).first()

    if not order:
        raise serializers.ValidationError({"order_id": "Order not found."})
    return order


def assign_delivery_person_to_order(order_identifier, delivery_slot_id, delivery_person_id, delivery_date):
    from orders.models import OrderStatus

    with transaction.atomic():
        order = _get_order_for_assignment(order_identifier)

        if not delivery_slot_id:
            raise serializers.ValidationError({"delivery_slot_id": "This field is required."})

        try:
            delivery_person = DeliveryPerson.objects.select_related('user').get(
                pk=delivery_person_id
            )
        except DeliveryPerson.DoesNotExist:
            raise serializers.ValidationError({
                "delivery_person_id": "Delivery person not found."
            })

        if not delivery_person.can_receive_orders:
            raise serializers.ValidationError({
                "delivery_person_id": "Delivery person must be active and have a completed profile."
            })

        delivery_date = _parse_delivery_date(delivery_date)

        try:
            slot = DeliverySlot.objects.get(id=delivery_slot_id, is_active=True)
        except DeliverySlot.DoesNotExist:
            raise serializers.ValidationError({
                "delivery_slot_id": "Invalid or inactive delivery slot."
            })

        schedule = _get_or_create_schedule(slot, delivery_date)
        previous_schedule_id = order.delivery_schedule_id
        is_same_schedule = previous_schedule_id == schedule.id

        now = timezone.localtime()
        if schedule.delivery_date < now.date():
            raise serializers.ValidationError({"delivery_date": "Delivery date has already passed."})
        if schedule.delivery_date == now.date() and schedule.slot.start_time <= now.time():
            raise serializers.ValidationError({"delivery_slot_id": "Delivery slot is no longer available."})
        if not is_same_schedule and not schedule.is_available:
            raise serializers.ValidationError({
                "delivery_slot_id": "Delivery slot is not available for this date."
            })

        if previous_schedule_id and not is_same_schedule:
            previous_schedule = DeliverySchedule.objects.select_for_update().get(id=previous_schedule_id)
            if previous_schedule.booked_orders > 0:
                previous_schedule.booked_orders -= 1
                previous_schedule.save(update_fields=['booked_orders', 'updated_at'])

        if not is_same_schedule:
            schedule.booked_orders += 1
            schedule.save(update_fields=['booked_orders', 'updated_at'])

        order.delivery_person = delivery_person
        order.delivery_schedule = schedule
        order.delivery_date = schedule.delivery_date
        order.delivery_slot_name = schedule.slot.name
        order.slot_start_time = schedule.slot.start_time
        order.slot_end_time = schedule.slot.end_time

        if not order.status or order.status.name not in ("Cancelled", "Failed", "Delivered"):
            assigned_status, _ = OrderStatus.objects.get_or_create(
                name='Assign to Delivery Partner'
            )
            order.status = assigned_status

        order.save(update_fields=[
            'delivery_person',
            'delivery_schedule',
            'delivery_date',
            'delivery_slot_name',
            'slot_start_time',
            'slot_end_time',
            'status',
        ])

    return order
