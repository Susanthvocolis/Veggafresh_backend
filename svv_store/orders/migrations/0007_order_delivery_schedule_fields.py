from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0001_initial'),
        ('orders', '0006_order_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_schedule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='delivery.deliveryschedule'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_slot_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='slot_end_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='slot_start_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['delivery_date'], name='order_deliv_59401b_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['delivery_schedule'], name='order_deliv_085616_idx'),
        ),
    ]
