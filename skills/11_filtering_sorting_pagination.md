# Skill: Filtering, Sorting & Pagination

## Overview

VeggaFresh uses DRF's built-in filter backends + `django-filters` + a custom paginator.
Understanding these patterns is essential for any list endpoint.

---

## 1. The Three Filter Backends

```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
```

| Backend | Query Param | Purpose |
|---|---|---|
| `DjangoFilterBackend` | `?status=Accepted` | Exact / range / relational filtering via `FilterSet` |
| `SearchFilter` | `?search=keyword` | Full-text search across declared `search_fields` |
| `OrderingFilter` | `?ordering=-created_at` | Column sorting via `ordering_fields` |

---

## 2. Creating a FilterSet (`filters.py`)

```python
import django_filters
from .models import Order

class OrderFilter(django_filters.FilterSet):
    # Exact match on related field
    user_id = django_filters.NumberFilter(field_name='user__id', lookup_expr='exact')

    # Partial match (case-insensitive)
    user_email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')

    # Date range
    order_date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    order_date_to   = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    # Partial match on related model name
    status = django_filters.CharFilter(field_name='status__name', lookup_expr='icontains')

    class Meta:
        model = Order
        fields = ['user_id', 'user_email', 'order_date_from', 'order_date_to', 'status']
```

### Common `lookup_expr` values

| Value | Behaviour |
|---|---|
| `exact` | Exact match |
| `icontains` | Case-insensitive partial match |
| `gte` | Greater than or equal (date/number) |
| `lte` | Less than or equal |
| `in` | Value in list |

---

## 3. On a `ModelViewSet` (auto-applied)

```python
class AdminFilterOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related('status', 'user').order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [IsSuperAdminOrHasOrderPermission]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class  = OrderFilter
    search_fields    = ['order_id', 'status__name']
    ordering_fields  = ['created_at', 'payment_method']
    ordering         = ['-created_at']   # ← default sort
```

DRF calls all backends automatically on `list()`.

---

## 4. On a Plain `ViewSet` (manual apply)

Plain `ViewSet`s do **not** auto-apply backends — call them manually:

```python
class AdminOrderViewSet(viewsets.ViewSet):
    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class  = OrderFilter
    search_fields    = ['order_id', 'status__name']
    ordering_fields  = ['created_at']
    ordering         = ['-created_at']

    def _get_queryset(self, request):
        qs = Order.objects.all().select_related('status', 'user').order_by('-created_at')
        qs = DjangoFilterBackend().filter_queryset(request, qs, self)
        qs = filters.SearchFilter().filter_queryset(request, qs, self)
        qs = filters.OrderingFilter().filter_queryset(request, qs, self)
        return qs

    def list(self, request):
        queryset = self._get_queryset(request)
        ...
```

---

## 5. Pagination — `CustomPageNumberPagination`

Located at `utils/pagination.py`:

```python
from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size           = 10       # Default items per page
    page_query_param    = 'page_no'
    page_size_query_param = 'page_size'
    max_page_size       = 100
```

### On a `ModelViewSet` — auto-applied via `settings.py`

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'utils.pagination.CustomPageNumberPagination',
}
```

No extra code needed — DRF wraps `list()` automatically.

### On a plain `ViewSet` or `APIView` — apply manually

```python
from utils.pagination import CustomPageNumberPagination

def list(self, request):
    queryset   = self._get_queryset(request)
    paginator  = CustomPageNumberPagination()
    page       = paginator.paginate_queryset(queryset, request)
    serializer = OrderSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
```

### Paginated response format

```json
{
  "count": 150,
  "next": "http://.../api/v1/orders/?page_no=2",
  "previous": null,
  "results": [ ... ]
}
```

### Query params

| Param | Default | Max | Example |
|---|---|---|---|
| `page_no` | `1` | — | `?page_no=3` |
| `page_size` | `10` | `100` | `?page_size=25` |

---

## 6. Why Orders Shuffle (and How to Prevent It)

PostgreSQL does **not guarantee order** without an explicit `ORDER BY`.
After any write (INSERT/UPDATE), rows may return in a different order.

**Always add `.order_by()` to every queryset:**

```python
# ❌ Wrong — shuffles after status updates
Order.objects.all()

# ✅ Correct
Order.objects.all().order_by('-created_at')
```

**For ModelViewSet, set both:**
```python
queryset = Order.objects.all().order_by('-created_at')   # base queryset
ordering = ['-created_at']                                # DRF default ordering
```

---

## 7. Quick Reference — All Filter Params on `/api/v1/orders/`

| Param | Example | Description |
|---|---|---|
| `?status=` | `?status=Accepted` | Filter by order status (partial) |
| `?order_id=` | `?order_id=260410` | Filter by order ID (partial) |
| `?user_id=` | `?user_id=5` | Filter by exact user ID |
| `?user_email=` | `?user_email=john` | Filter by user email (partial) |
| `?user_mobile=` | `?user_mobile=9999` | Filter by mobile (partial) |
| `?payment_method=` | `?payment_method=cod` | `online` or `cod` |
| `?order_date_from=` | `?order_date_from=2025-04-01` | Orders from date |
| `?order_date_to=` | `?order_date_to=2025-04-10` | Orders up to date |
| `?search=` | `?search=Accepted` | Search order_id + status |
| `?ordering=` | `?ordering=-created_at` | Sort field (prefix `-` for desc) |
| `?page_no=` | `?page_no=2` | Page number |
| `?page_size=` | `?page_size=25` | Items per page (max 100) |
