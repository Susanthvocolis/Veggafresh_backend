# Skill: Optimization Checklist — Mandatory Patterns for New Files

## Overview

Every new view, serializer, or model created in VeggaFresh **must** follow these patterns.
This checklist prevents the most common performance problems found in this codebase.

---

## ✅ Checklist — New View File

Before finishing any new view, check every item below:

### 1. `select_related` — Always on FK / OneToOne fields you READ

```python
# ❌ Missing — hits DB for each related field access
Order.objects.all()

# ✅ Correct — JOINs in one query
Order.objects.all().select_related('status', 'user', 'delivery_person', 'address')
```

**Rule:** Any field accessed in the serializer that is a ForeignKey or OneToOne **must** be in `select_related`.

---

### 2. `prefetch_related` — Always on reverse FK / M2M / deep chains

```python
# ❌ Missing — N+1 queries for items, images, payments
Order.objects.all().select_related('status', 'user')

# ✅ Correct — all nested data in a small fixed number of queries
Order.objects.all()\
    .select_related('status', 'user', 'delivery_person', 'address')\
    .prefetch_related(
        'items__product_variant__product__images',  # item chain
        'payment_set',                              # payments
    )
```

**Rule:** Any reverse relation accessed in the serializer (`obj.items.all()`, `obj.payment_set`, etc.) **must** be prefetched.

---

### 3. `.order_by()` — Always explicit, never trust default

```python
# ❌ Wrong — shuffles after any DB write (INSERT/UPDATE)
Order.objects.all()

# ✅ Correct
Order.objects.all().order_by('-created_at')
```

**Rule:** Every list queryset **must** have `.order_by()`. Most lists default to `-created_at` (newest first).

---

### 4. Payment N+1 — Use prefetch, not per-object query

```python
# ❌ Wrong — fires 1 query per order in any list
Payment.objects.filter(order=obj).first()

# ✅ Correct — prefetch in the view, read from cache in serializer
# View:
queryset.prefetch_related('payment_set')

# Serializer:
def _get_payment(self, obj):
    prefetched = getattr(obj, '_prefetched_objects_cache', {})
    if 'payment_set' in prefetched:
        payments = prefetched['payment_set']
        return payments[0] if payments else None
    if not hasattr(obj, '_cached_payment'):
        obj._cached_payment = Payment.objects.filter(order=obj).first()
    return obj._cached_payment
```

---

### 5. Plain `ViewSet` — Manually apply filter backends

Plain `ViewSet`s do NOT auto-apply backends — do it explicitly:

```python
class MyViewSet(viewsets.ViewSet):
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class  = MyFilter
    search_fields    = ['name', 'status__name']
    ordering_fields  = ['created_at']
    ordering         = ['-created_at']

    def _get_queryset(self, request):
        qs = MyModel.objects.select_related(...).prefetch_related(...).order_by('-created_at')
        qs = DjangoFilterBackend().filter_queryset(request, qs, self)
        qs = filters.SearchFilter().filter_queryset(request, qs, self)
        qs = filters.OrderingFilter().filter_queryset(request, qs, self)
        return qs
```

---

### 6. Pagination — Required on every list endpoint

```python
# ❌ Wrong — dumps all rows, gets slower as data grows
return Response(serializer.data)

# ✅ Correct — use CustomPageNumberPagination for plain ViewSet/APIView
from utils.pagination import CustomPageNumberPagination

def list(self, request):
    queryset   = self._get_queryset(request)
    paginator  = CustomPageNumberPagination()
    page       = paginator.paginate_queryset(queryset, request)
    serializer = MySerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
```

For `ModelViewSet` — pagination is auto-applied if `DEFAULT_PAGINATION_CLASS` has a `page_size`.

---

### 7. Redis Cache — Correct pattern (param-aware key + set before return)

```python
# ❌ Wrong — cache.set() AFTER a return never executes
page = paginator.paginate_queryset(queryset, request)
if page is not None:
    return paginator.get_paginated_response(...)   # returns here
cache.set(cache_key, ...)                          # NEVER REACHED

# ✅ Correct
def get(self, request):
    params    = request.query_params
    cache_key = f"my_list_p{params.get('page',1)}_ps{params.get('page_size',10)}_q{params.get('search','')}"

    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    queryset  = ...
    page      = paginator.paginate_queryset(queryset, request)
    serializer = MySerializer(page, many=True)
    response  = paginator.get_paginated_response(serializer.data)

    cache.set(cache_key, response.data, timeout=60 * 5)   # 5 minutes
    return response
```

**Cache key rules:**
- Include ALL query params that affect the result (page, page_size, filters, search)
- Invalidate on create/update: `cache.delete(cache_key)` or use a pattern

---

## ✅ Checklist — New Serializer File

### 8. Nested serializers — Always `read_only=True`

```python
class OrderSerializer(serializers.ModelSerializer):
    items           = OrderItemSerializer(many=True, read_only=True)   # ← required
    delivery_person = DeliveryPersonSerializer(read_only=True)          # ← required
    address         = AddressSerializer(read_only=True)                 # ← required
```

---

### 9. Computed fields — Use `SerializerMethodField`, not model properties in loops

```python
# ❌ Wrong — model property fires DB query per object in a list
class OrderItemSerializer(...):
    total = serializers.SerializerMethodField()
    def get_total(self, obj):
        return obj.product_variant.price * obj.quantity  # extra DB hit if not prefetched

# ✅ Correct — ensure product_variant is prefetched in the view
```

---

### 10. Separate Admin vs User serializers when fields differ

```python
# User serializer — full data including product_image
class OrderItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    ...

# Admin serializer — leaner, no product_image
class AdminOrderItemSerializer(serializers.ModelSerializer):
    # product_image excluded for speed
    ...

class AdminOrderSerializer(serializers.ModelSerializer):
    items = AdminOrderItemSerializer(many=True, read_only=True)
```

---

## ✅ Checklist — New Model File

### 11. Always add DB indexes on filtered/sorted fields

```python
class Meta:
    db_table = 'my_model'
    indexes = [
        models.Index(fields=['user']),         # if filtering by user
        models.Index(fields=['status']),        # if filtering by status
        models.Index(fields=['created_at']),    # if sorting by date
        models.Index(fields=['is_active']),     # if filtering by active flag
    ]
```

---

### 12. Use DB `aggregate()` not Python loops for totals

```python
# ❌ Wrong — loads all items into Python memory
subtotal = sum(item.price * item.qty for item in self.items.all())

# ✅ Correct — single SQL query
from django.db.models import Sum, F, Case, When, DecimalField as DBDecimal

result = self.items.aggregate(
    subtotal=Sum(
        Case(
            When(product_variant__discounted_price__gt=0,
                 then=F('product_variant__discounted_price') * F('quantity')),
            default=F('product_variant__price') * F('quantity'),
            output_field=DBDecimal(max_digits=10, decimal_places=2)
        )
    )
)
subtotal = result['subtotal'] or Decimal('0.00')
```

---

## Quick Reference — Full Optimized View Pattern

Copy this as your starting template for any new admin list view:

```python
class MyNewViewSet(viewsets.ViewSet):
    """
    GET /api/v1/my-resource/
    Supports filtering, searching, sorting, pagination.
    """
    permission_classes = [IsSuperAdminOrHasXPermission]

    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class  = MyFilter
    search_fields    = ['name', 'status__name']
    ordering_fields  = ['created_at', 'name']
    ordering         = ['-created_at']

    def _get_queryset(self, request):
        qs = (
            MyModel.objects.all()
            .select_related('status', 'user', 'related_fk')     # all FK fields used in serializer
            .prefetch_related(
                'items__product_variant__product__images',        # all reverse FK chains
                'payment_set',                                    # payment N+1 fix
            )
            .order_by('-created_at')                             # always explicit
        )
        qs = DjangoFilterBackend().filter_queryset(request, qs, self)
        qs = filters.SearchFilter().filter_queryset(request, qs, self)
        qs = filters.OrderingFilter().filter_queryset(request, qs, self)
        return qs

    def list(self, request):
        queryset  = self._get_queryset(request)
        paginator = CustomPageNumberPagination()
        page      = paginator.paginate_queryset(queryset, request)
        serializer = MySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            obj = (
                MyModel.objects
                .select_related('status', 'user', 'related_fk')
                .prefetch_related('items__product_variant__product__images', 'payment_set')
                .get(pk=pk)
            )
            serializer = MySerializer(obj)
            return Response(serializer.data)
        except MyModel.DoesNotExist:
            return Response({'message': 'Not found'}, status=404)
```

---

## What NOT to Do — Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| `Model.objects.all()` with no `select_related` | N+1 on every FK access | Add `select_related` |
| `self.items.all()` in a serializer loop | N+1 per parent row | `prefetch_related` in view |
| `Payment.objects.filter(order=obj).first()` in a list | 1 query per order | `prefetch_related('payment_set')` |
| `.order_by()` missing | Shuffles after writes | Always add `order_by('-created_at')` |
| `cache.set()` after a `return` | Cache never populates | Move set before return |
| Single `cache_key` for all pages/filters | Page 2 returns page 1 cache | Include all params in key |
| `sum(... for item in self.items.all())` in model | Loads all rows to Python | Use DB `aggregate()` |
| No pagination on list endpoints | Dumps all rows, slows as data grows | Use `CustomPageNumberPagination` |
