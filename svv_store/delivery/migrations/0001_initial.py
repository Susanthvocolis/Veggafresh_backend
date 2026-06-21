from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DeliverySlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'delivery_slot',
                'ordering': ['sort_order', 'start_time', 'name'],
            },
        ),
        migrations.CreateModel(
            name='DeliverySchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_date', models.DateField()),
                ('max_orders', models.PositiveIntegerField(default=0)),
                ('booked_orders', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('is_blocked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slot', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='schedules', to='delivery.deliveryslot')),
            ],
            options={
                'db_table': 'delivery_schedule',
                'ordering': ['delivery_date', 'slot__sort_order', 'slot__start_time'],
            },
        ),
        migrations.AddIndex(
            model_name='deliveryslot',
            index=models.Index(fields=['is_active', 'sort_order'], name='delivery_sl_is_acti_7cc41d_idx'),
        ),
        migrations.AddIndex(
            model_name='deliveryslot',
            index=models.Index(fields=['start_time', 'end_time'], name='delivery_sl_start_t_3e7b1a_idx'),
        ),
        migrations.AddConstraint(
            model_name='deliveryschedule',
            constraint=models.UniqueConstraint(fields=('delivery_date', 'slot'), name='uniq_delivery_schedule_date_slot'),
        ),
        migrations.AddConstraint(
            model_name='deliveryschedule',
            constraint=models.CheckConstraint(check=models.Q(('booked_orders__lte', models.F('max_orders'))), name='delivery_schedule_booked_lte_max'),
        ),
        migrations.AddIndex(
            model_name='deliveryschedule',
            index=models.Index(fields=['delivery_date', 'is_active', 'is_blocked'], name='delivery_sc_deliver_403dc2_idx'),
        ),
        migrations.AddIndex(
            model_name='deliveryschedule',
            index=models.Index(fields=['slot', 'delivery_date'], name='delivery_sc_slot_id_8675e0_idx'),
        ),
    ]
