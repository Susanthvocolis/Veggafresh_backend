# Skill: Migrations, Models & Database

## Overview
VeggaFresh uses **PostgreSQL** via `psycopg2-binary`, with Django's ORM. All secrets are loaded from `.env`. This skill covers migration workflow, model conventions, and database best practices for this project.

---

## 1. Database Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

---

## 2. Migration Commands

Always run from `svv_store/` directory:

```bash
cd svv_store

# Create new migration files for all changed models
python manage.py makemigrations

# Create migration for a specific app only
python manage.py makemigrations <app_name>

# Apply all pending migrations
python manage.py migrate

# Apply migrations for a specific app
python manage.py migrate <app_name>

# Check for unapplied migrations
python manage.py showmigrations

# Show the SQL for a migration (before applying)
python manage.py sqlmigrate <app> <migration_number>

# Rollback to a specific migration
python manage.py migrate <app> <migration_number>
```

---

## 3. Model Conventions in This Project

### Naming

| Convention | Example |
|------------|---------|
| `db_table` always explicitly set | `db_table = 'product'` |
| Indexes defined in `Meta.indexes` | `models.Index(fields=['category'])` |
| Timestamps use `auto_now_add` / `auto_now` | `created_at`, `updated_at` |
| Soft delete via `is_active` | Products, not actual deletes |

---

### Standard Meta Block Pattern

```python
class Meta:
    db_table = 'my_model'          # Always explicit
    indexes = [
        models.Index(fields=['user']),
        models.Index(fields=['created_at']),
    ]
    ordering = ['-created_at']     # Optional default ordering
```

---

### ForeignKey Patterns

```python
# Nullable FK (don't cascade user deletes to orders)
user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

# Hard cascade (delete OrderItems when Order is deleted)
order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
```

---

## 4. Creating a New Model — Checklist

1. **Define the model** in `<app>/models.py`
2. **Set `db_table`** explicitly in Meta
3. **Add indexes** for all FK fields and commonly filtered/sorted fields
4. **Run `makemigrations`** and inspect the generated SQL
5. **Run `migrate`**
6. **Register in `admin.py`** so it's visible in Django Admin
7. **Create serializer** in `<app>/serializers.py`
8. **Create views + URLs**

---

## 5. Model Field Reference (Common Patterns Used)

```python
from django.db import models
from django.utils import timezone

# Text
name = models.CharField(max_length=255)
slug = models.SlugField(unique=True, blank=True)
description = models.TextField(blank=True)

# Numbers
price = models.DecimalField(max_digits=10, decimal_places=2)
quantity = models.DecimalField(max_digits=5, decimal_places=2)
stock = models.PositiveIntegerField(default=0)

# Boolean
is_active = models.BooleanField(default=True)
is_available = models.BooleanField(default=True)

# Timestamps
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)

# Choices
unit = models.CharField(max_length=10, choices=[
    ('kg', 'Kilogram'), ('g', 'Gram'), ('l', 'Litre')
])

# ForeignKey
user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
```

---

## 6. Custom `save()` Patterns

### Auto-generate slug

```python
from django.utils.text import slugify

def save(self, *args, **kwargs):
    if not self.pk or self.name != MyModel.objects.get(pk=self.pk).name:
        self.slug = slugify(self.name)
    super().save(*args, **kwargs)
```

### Auto-generate order ID (date + sequence)

```python
def save(self, *args, **kwargs):
    if not self.order_id:
        today = timezone.now().date()
        prefix = today.strftime('%y%m%d')  # e.g., 260409
        count_today = Order.objects.filter(created_at__date=today).count() + 1
        suffix = str(count_today).zfill(3) if count_today < 100 else str(count_today)
        self.order_id = f"{prefix}{suffix}"
    super().save(*args, **kwargs)
```

---

## 7. Useful ORM Queries in This Project

### User's cart with all items

```python
from cart.models import Cart

cart = Cart.objects.prefetch_related('items__product_variant__product').get(user=user)
```

### Orders with full details (efficient)

```python
from orders.models import Order

orders = Order.objects.select_related(
    'status', 'user', 'delivery_person', 'address'
).prefetch_related(
    'items__product_variant__product__images'
).filter(user=user).order_by('-created_at')
```

### Monthly sales aggregation

```python
from django.db.models.functions import TruncMonth
from django.db.models import Count

sales = (
    Order.objects
    .annotate(month=TruncMonth('created_at'))
    .values('month')
    .annotate(order_count=Count('id'))
    .order_by('month')
)
```

### Top selling product this month

```python
from django.db.models import Sum
from django.utils import timezone

start_of_month = timezone.now().replace(day=1)

top = (
    OrderItem.objects
    .filter(order__created_at__gte=start_of_month)
    .values('product_variant')
    .annotate(total_quantity=Sum('quantity'))
    .order_by('-total_quantity')
    .first()
)
```

---

## 8. Django Admin Registration Pattern

```python
# <app>/admin.py
from django.contrib import admin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    search_fields = ['name']
    list_filter = ['is_active']
    ordering = ['-created_at']
```

---

## 9. Redis Cache (django-redis)

```python
# Configured in settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://...',
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}
```

### Common Cache Operations

```python
from django.core.cache import cache

# Set (5 min timeout)
cache.set('my_key', data, timeout=60 * 5)

# Get (returns None if not found)
data = cache.get('my_key')

# Delete
cache.delete('my_key')

# Delete multiple keys by pattern
cache.delete_pattern('user_wishlist_*')
```

Apps using caching:
- `wishlist/views.py` — per-user wishlist (5 min)
- `products/views.py` — product list cache (5 min, key: `product_list_cache`)
