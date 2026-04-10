# Skill: Permissions & Role-Based Access Control (RBAC)

## Overview

VeggaFresh has 3 user roles and a granular module-permission system for admin employees.
Understanding this is critical before adding any new admin endpoint.

---

## 1. The Three Roles

Defined in `users/models.py`:

```python
class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN'   # Full access to everything
        ADMIN       = 'ADMIN'         # Access gated by ModulePermission
        USER        = 'USER'          # Customer — access own data only
```

---

## 2. The `ModulePermission` Model

Each `ADMIN` user has a linked `ModulePermission` row (one-to-one):

```python
class ModulePermission(models.Model):
    employee = models.OneToOneField(User, related_name='permissions', ...)

    # Products
    can_add_product    = models.BooleanField(default=False)
    can_edit_product   = models.BooleanField(default=False)
    can_delete_product = models.BooleanField(default=False)
    can_view_product   = models.BooleanField(default=False)

    # Orders
    can_manage_orders          = models.BooleanField(default=False)
    can_manage_delivery_status = models.BooleanField(default=False)

    # Payments
    can_view_payment = models.BooleanField(default=False)

    # Users
    can_view_users   = models.BooleanField(default=False)
    can_update_users = models.BooleanField(default=False)
    can_delete_users = models.BooleanField(default=False)
    # ... (categories, subcategories also)
```

Access via: `user.permissions.can_manage_orders`

---

## 3. How a Custom Permission Class Works

Example from `orders/permissions.py`:

```python
from rest_framework.permissions import BasePermission

class IsSuperAdminOrHasOrderPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        # SUPER_ADMIN: full access, no checks needed
        if user.role == user.Role.SUPER_ADMIN:
            return True

        # ADMIN: check specific module permission
        if user.role == user.Role.ADMIN:
            try:
                perms = user.permissions   # ModulePermission instance
            except:
                return False

            action = view.action   # e.g. 'list', 'retrieve', 'update_status'

            if action in ['list', 'retrieve', 'get_by_status', 'status_options']:
                return perms.can_manage_orders

            if action == 'update_status':
                return perms.can_manage_delivery_status

            if action in ['update', 'partial_update', 'destroy']:
                return perms.can_manage_orders

        return False   # USER role: denied for admin endpoints
```

---

## 4. Applying Permissions to Views

```python
# Single permission class
class AdminOrderViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperAdminOrHasOrderPermission]

# User-only endpoint (any authenticated user)
class MyOrdersView(APIView):
    permission_classes = [IsAuthenticated]

# Multiple permissions (all must pass)
class AdminProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdminOrHasOrderPermission]
```

---

## 5. Creating a New Permission Class

When adding a new admin module, create a permission class that follows the same pattern:

```python
# e.g. for a new "Reports" module
class IsSuperAdminOrHasReportPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == user.Role.SUPER_ADMIN:
            return True
        if user.role == user.Role.ADMIN:
            try:
                perms = user.permissions
            except:
                return False
            # Map DRF actions to permissions
            if view.action in ['list', 'retrieve']:
                return perms.can_view_payment   # reuse existing or add new field
        return False
```

> **If you add a new module permission field**, remember to:
> 1. Add the field to `ModulePermission` model in `users/models.py`
> 2. Run `python manage.py makemigrations && python manage.py migrate`
> 3. Update the Django admin to expose it

---

## 6. How `view.action` Maps to HTTP Methods

| HTTP Method | ViewSet Action | Use |
|---|---|---|
| `GET /orders/` | `list` | List all |
| `GET /orders/3/` | `retrieve` | Single item |
| `POST /orders/` | `create` | Create |
| `PUT /orders/3/` | `update` | Full update |
| `PATCH /orders/3/` | `partial_update` | Partial update |
| `DELETE /orders/3/` | `destroy` | Delete |
| `PATCH /orders/3/update-status/` | `update_status` | Custom `@action` |

---

## 7. Checking Role & Permissions Anywhere

```python
# In a view
def get(self, request):
    user = request.user
    if user.role == user.Role.SUPER_ADMIN:
        ...
    if user.role == user.Role.ADMIN:
        if user.permissions.can_manage_orders:
            ...

# In a serializer context
def get_field(self, obj):
    request = self.context.get('request')
    if request and request.user.role == 'SUPER_ADMIN':
        ...
```

---

## 8. Common Permission Errors

| Error | Cause | Fix |
|---|---|---|
| `403 Forbidden` | User role not allowed | Check `permission_classes` on the view |
| `AttributeError: User has no permissions` | `ADMIN` user has no `ModulePermission` row | Create `ModulePermission` for the user in admin panel |
| `RelatedObjectDoesNotExist` | Same — `user.permissions` doesn't exist | Handle with `try/except` in permission class |
| `401 Unauthorized` | Missing/expired JWT token | Refresh token or re-login |
