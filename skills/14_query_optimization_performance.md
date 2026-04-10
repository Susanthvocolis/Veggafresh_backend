# Skill: Query Optimization & Performance

## Overview

VeggaFresh serves a grocery store API where order lists, product catalogs, and analytics can involve many related objects. Poor querysets cause N+1 problems, slow responses, and shuffled data. This skill covers the patterns actually used in the project.

---

## 1. The N+1 Problem — What It Is

Without optimization, accessing a related object in a loop hits the DB once per row:

```python
# ❌ N+1: 1 query for orders + N queries for user/status per order
orders = Order.objects.all()
for order in orders:
    print(order.user.email)     # DB hit each time
    print(order.status.name)    # DB hit each time
```

**Fix: `select_related`** (JOINs, for FK/OneToOne):

```python
# ✅ 1 query with JOIN
orders = Order.objects.all().select_related('status', 'user', 'delivery_person')
```

---

## 2. `select_related` — FK & OneToOne (SQL JOIN)

Use for **ForeignKey** and **OneToOne** fields:

```python
# Orders — joins status, user, delivery_person in one query
Order.objects.all().select_related('status', 'user', 'delivery_person')

# Deep traversal (follow the chain)
OrderItem.objects.select_related('product_variant__product')
```

---

## 3. `prefetch_related` — ManyToMany & Reverse FK

Use for **reverse FK** (e.g. `order.items`) and **M2M**:

```python
# Prefetch items + their variant + product + images in separate efficient queries
Order.objects.prefetch_related(
    'items__product_variant__product__images'
)

# Combined
Order.objects.select_related('status', 'user', 'address')\
             .prefetch_related('items__product_variant__product__images')
```

---

## 4. Always `order_by()` — Never Trust Default Order

PostgreSQL returns rows in **undefined order** after writes. Always be explicit:

```python
# ❌ May shuffle after status update
Order.objects.all()

# ✅ Stable newest-first sort
Order.objects.all().order_by('-created_at')

# ✅ On ModelViewSet — set BOTH queryset order and DRF default
class MyViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    ordering = ['-created_at']   # DRF OrderingFilter default
```

---

## 5. `.values()` — Read-Only Flat Dicts (Analytics)

For analytics where you don't need full model instances:

```python
# Returns list of dicts, not model objects — much faster
OrderStatus.objects.all().values('id', 'name')

# Aggregate per group
from django.db.models import Count, Sum
Order.objects.values('status__name').annotate(count=Count('id'))
```

---

## 6. `annotate()` & Aggregation (Used in Analytics Views)

```python
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth

# Sales per month
Order.objects.annotate(month=TruncMonth('created_at'))\
             .values('month')\
             .annotate(order_count=Count('id'))\
             .order_by('month')

# Revenue calculation (quantity × discounted_price)
OrderItem.objects.aggregate(
    revenue=Sum(F('quantity') * F('product_variant__discounted_price'))
)

# Most sold product
OrderItem.objects.values('product_variant')\
                 .annotate(total_qty=Sum('quantity'))\
                 .order_by('-total_qty')\
                 .first()
```

---

## 7. Database Indexes in This Project

All key lookup/sort fields are indexed in `model.Meta`:

```python
class Order(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['user']),       # fast user filter
            models.Index(fields=['status']),     # fast status filter
            models.Index(fields=['created_at']), # fast date sort
            models.Index(fields=['order_id']),   # fast ID lookup
        ]
```

**Rule:** Any field you filter or sort by in a large table should have an index.

---

## 8. Caching with Redis

Django Redis is configured for the project. Use it for frequently-read, rarely-changed data:

```python
from django.core.cache import cache

# Cache for 5 minutes
CACHE_TTL = 60 * 5

def get(self, request):
    cache_key = f'products_list_{request.user.id}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    queryset   = Product.objects.filter(is_active=True).select_related(...)
    serializer = ProductSerializer(queryset, many=True)
    cache.set(cache_key, serializer.data, CACHE_TTL)
    return Response(serializer.data)

# Invalidate cache on write
def perform_update(self, serializer):
    serializer.save()
    cache.delete('products_list_*')   # or use specific key
```

---

## 9. Queryset Slicing (Avoid for Large Sets)

The `GetAllOrderViewSet` uses Python slicing — this is less efficient than DB-level pagination:

```python
# ❌ Less efficient — evaluates then slices in Python
queryset[start:end]

# ✅ Better — use DRF's paginator (SQL LIMIT/OFFSET)
paginator = CustomPageNumberPagination()
page = paginator.paginate_queryset(queryset, request)
```

---

## 10. Checking Slow Queries (Django Shell)

```python
# In shell: cd svv_store && python manage.py shell
from django.db import connection

# Run any queryset
from orders.models import Order
qs = list(Order.objects.all().select_related('status', 'user'))

# See all SQL queries fired
for q in connection.queries:
    print(q['sql'])
    print(q['time'])
```

Add `DEBUG = True` in settings to enable query logging.
