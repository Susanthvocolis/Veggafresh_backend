from django.db import migrations, models
import django.db.models.deletion


def move_delivery_people(apps, schema_editor):
    User = apps.get_model('users', 'User')
    LegacyDeliveryPerson = apps.get_model('orders', 'DeliveryPerson')
    DeliveryPerson = apps.get_model('delivery', 'DeliveryPerson')
    Order = apps.get_model('orders', 'Order')

    profile_ids = {}
    for legacy in LegacyDeliveryPerson.objects.all().iterator():
        mobile = (legacy.mobile or '').strip()[:15] or None
        user = User.objects.filter(mobile=mobile).first() if mobile else None
        if user is None:
            user = User(
                username=mobile or f'delivery-{legacy.pk}',
                first_name=(legacy.name or '')[:150],
                mobile=mobile,
                role='DELIVERY_PERSON',
                profile_complete=False,
                is_active=True,
            )
            user.password = '!'
            user.save()
        else:
            user.role = 'DELIVERY_PERSON'
            if not user.first_name:
                user.first_name = (legacy.name or '')[:150]
            user.profile_complete = False
            user.save(update_fields=['role', 'first_name', 'profile_complete'])

        profile, _ = DeliveryPerson.objects.get_or_create(
            user=user,
            defaults={'status': 'INACTIVE'},
        )
        profile_ids[legacy.pk] = profile.pk

    for legacy_id, profile_id in profile_ids.items():
        Order.objects.filter(delivery_person_id=legacy_id).update(
            delivery_profile_id=profile_id,
        )

    delivered = apps.get_model('orders', 'OrderStatus')
    delivered.objects.filter(name='Delivery Status Update').update(name='Delivered')


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('delivery', '0002_delivery_person'),
        ('orders', '0007_order_delivery_schedule_fields'),
        ('users', '0003_add_delivery_person_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_profile',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='orders',
                to='delivery.deliveryperson',
            ),
        ),
        migrations.RunPython(move_delivery_people, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='order',
            name='delivery_person',
        ),
        migrations.DeleteModel(
            name='DeliveryPerson',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='delivery_profile',
            new_name='delivery_person',
        ),
    ]
