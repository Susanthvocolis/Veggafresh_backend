from rest_framework.permissions import BasePermission


class IsSuperAdminOrCanManageDelivery(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.role == user.Role.SUPER_ADMIN:
            return True

        if user.role == user.Role.ADMIN:
            try:
                perms = user.permissions
            except Exception:
                return False
            return perms.can_manage_orders

        return False
