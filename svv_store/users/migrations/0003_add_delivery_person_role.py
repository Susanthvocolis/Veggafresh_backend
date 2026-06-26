from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_modulepermission_can_add_banner_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('SUPER_ADMIN', 'Super Admin'),
                    ('ADMIN', 'Admin'),
                    ('DELIVERY_PERSON', 'Delivery Person'),
                    ('USER', 'User'),
                ],
                default='USER',
                max_length=20,
            ),
        ),
    ]
