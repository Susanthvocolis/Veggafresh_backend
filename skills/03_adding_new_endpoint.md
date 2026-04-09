# Skill: Adding a New API Endpoint

## Overview
This skill covers the standard pattern for creating a new API endpoint in VeggaFresh Backend, following the existing architecture conventions.

---

## 1. Architecture Conventions

- All API routes live under `/api/v1/` (defined in `svv_store/urls.py`)
- Every app has its own `urls.py`, `views.py` (or `views/` directory), `serializers.py`, `models.py`, `permissions.py`
- All responses go through `utils.renderers.CustomRenderer` — **always** use DRF's `Response()` class
- Pagination is handled by `utils.pagination.CustomPageNumberPagination`
- Views split by role when needed: `views/user_views.py`, `views/admin_views.py`

---

## 2. Step-by-Step: Adding a New Endpoint

### Step 1 — Define the Model (if needed)

```python
# <app>/models.py
from django.db import models

class MyModel(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'my_model'
        indexes = [
            models.Index(fields=['name']),
        ]
```

Run migrations:

```bash
cd svv_store
python manage.py makemigrations <app>
python manage.py migrate
```

---

### Step 2 — Create the Serializer

```python
# <app>/serializers.py
from rest_framework import serializers
from .models import MyModel

class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = '__all__'
```

---

### Step 3 — Create the View

#### Option A: ViewSet (CRUD + Router)

```python
# <app>/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import MyModel
from .serializers import MyModelSerializer

class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    permission_classes = [IsAuthenticated]
```

#### Option B: APIView (Custom Logic)

```python
# <app>/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class MyCustomView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {"message": "Hello"}
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        # process request.data
        return Response({"created": True}, status=status.HTTP_201_CREATED)
```

---

### Step 4 — Register the URL

#### With Router (for ViewSets):

```python
# <app>/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MyModelViewSet

router = DefaultRouter()
router.register(r'my-models', MyModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

#### Manual path (for APIViews):

```python
# <app>/urls.py
from django.urls import path
from .views import MyCustomView

urlpatterns = [
    path('my-endpoint/', MyCustomView.as_view(), name='my-endpoint'),
    path('my-endpoint/<int:pk>/', MyCustomView.as_view(), name='my-endpoint-detail'),
]
```

#### Register in main `svv_store/urls.py`:

```python
# svv_store/urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('api/v1/', include('<app>.urls')),
]
```

---

### Step 5 — Add Permissions (if needed)

```python
# <app>/permissions.py
from rest_framework.permissions import BasePermission
from users.models import User

class IsSuperAdminOrHasCustomPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == User.Role.SUPER_ADMIN:
            return True
        # Check module permission
        try:
            return user.permissions.can_view_product  # example
        except AttributeError:
            return False
```

---

## 3. Common Patterns

### Filtering with `django-filter`

```python
# <app>/filters.py
from django_filters import rest_framework as filters
from .models import MyModel

class MyModelFilter(filters.FilterSet):
    class Meta:
        model = MyModel
        fields = ['name', 'is_active']
```

```python
# In ViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class MyModelViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MyModelFilter
    search_fields = ['name']
    ordering_fields = ['created_at']
```

---

### Caching a View

```python
from django.core.cache import cache

class MyView(APIView):
    def get(self, request):
        cache_key = f"my_data_{request.user.id}"
        data = cache.get(cache_key)
        if not data:
            # compute data
            data = {"result": "value"}
            cache.set(cache_key, data, timeout=60 * 5)  # 5 min
        return Response(data)
```

Always invalidate cache after mutations:
```python
cache.delete(f"my_data_{user.id}")
```

---

### Custom Router Action (extra endpoint on ViewSet)

```python
from rest_framework.decorators import action

class MyModelViewSet(viewsets.ViewSet):

    @action(detail=True, methods=['patch'], url_path='activate')
    def activate(self, request, pk=None):
        obj = MyModel.objects.get(pk=pk)
        obj.is_active = True
        obj.save()
        return Response({"message": "Activated"})

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        return Response({"count": MyModel.objects.count()})
```

Generated URLs:
- `PATCH /api/v1/my-models/<pk>/activate/`
- `GET /api/v1/my-models/summary/`

---

## 4. Response Format Note

All responses are wrapped by `utils.renderers.CustomRenderer`. Do **not** manually wrap responses — just return data directly in `Response()`.

```python
# Correct ✅
return Response({"message": "Done"}, status=status.HTTP_200_OK)
return Response(serializer.data, status=status.HTTP_201_CREATED)

# Avoid wrapping manually ❌
return Response({"status": "success", "data": serializer.data})
```

---

## 5. Testing the Endpoint

```bash
# Run all tests
python manage.py test

# Run app-specific tests
python manage.py test <app_name>

# Run a single test class
python manage.py test <app>.tests.TestMyView
```

Test file location: `<app>/tests.py`
