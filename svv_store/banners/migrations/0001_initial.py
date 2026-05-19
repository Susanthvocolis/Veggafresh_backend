from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('subtitle', models.CharField(blank=True, max_length=500)),
                ('image', models.TextField()),
                ('mobile_image', models.TextField(blank=True, null=True)),
                ('link_url', models.URLField(blank=True)),
                ('banner_type', models.CharField(
                    choices=[
                        ('hero', 'Hero Slider'),
                        ('offer', 'Offer Strip'),
                        ('category', 'Category Banner'),
                        ('app_promo', 'App Promotion'),
                    ],
                    default='hero',
                    max_length=20,
                )),
                ('position', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_banners',
                    to='users.user',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='updated_banners',
                    to='users.user',
                )),
            ],
            options={
                'db_table': 'banner',
                'ordering': ['position', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='banner',
            index=models.Index(fields=['is_active', 'banner_type'], name='banner_is_ac_banner__idx'),
        ),
        migrations.AddIndex(
            model_name='banner',
            index=models.Index(fields=['position'], name='banner_positio_idx'),
        ),
        migrations.AddIndex(
            model_name='banner',
            index=models.Index(fields=['start_date', 'end_date'], name='banner_start_d_idx'),
        ),
    ]
