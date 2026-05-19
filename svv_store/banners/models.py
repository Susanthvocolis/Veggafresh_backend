from django.db import models
from django.utils import timezone
from users.models import User


BANNER_TYPE_CHOICES = [
    ('hero',       'Hero Slider'),
    ('offer',      'Offer Strip'),
    ('category',   'Category Banner'),
    ('app_promo',  'App Promotion'),
]


class Banner(models.Model):
    """
    Hero / rotating slider / strip banners shown on the storefront.
    Supports scheduling via start_date / end_date.
    """
    title        = models.CharField(max_length=255)
    subtitle     = models.CharField(max_length=500, blank=True)
    image        = models.TextField()
    mobile_image = models.TextField(null=True, blank=True)
    link_url     = models.URLField(blank=True)
    banner_type  = models.CharField(max_length=20, choices=BANNER_TYPE_CHOICES, default='hero')
    position     = models.PositiveIntegerField(default=0)
    is_active    = models.BooleanField(default=True)
    def get_default_end_date():
        return timezone.datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    start_date   = models.DateTimeField(null=True, blank=True)
    end_date     = models.DateTimeField(null=True, blank=True, default=get_default_end_date)

    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='created_banners')
    updated_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='updated_banners')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'banner'
        ordering = ['position', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'banner_type']),
            models.Index(fields=['position']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"[{self.banner_type.upper()}] {self.title}"
