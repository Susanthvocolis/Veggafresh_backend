from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('delivery', '0001_initial'),
        ('users', '0003_add_delivery_person_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryPerson',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('vehicle_type', models.CharField(blank=True, max_length=100, null=True)),
                (
                    'vehicle_number',
                    models.CharField(blank=True, max_length=50, null=True, unique=True),
                ),
                (
                    'address',
                    models.TextField(blank=True, null=True),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('ACTIVE', 'Active'),
                            ('INACTIVE', 'Inactive'),
                            ('ON_DUTY', 'On Duty'),
                            ('OFF_DUTY', 'Off Duty'),
                        ],
                        default='INACTIVE',
                        max_length=20,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='delivery_profile',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'db_table': 'delivery_person_profile',
                'ordering': ['user__first_name', 'user__mobile'],
            },
        ),
        migrations.AddIndex(
            model_name='deliveryperson',
            index=models.Index(fields=['status'], name='delivery_person_status_idx'),
        ),
    ]
