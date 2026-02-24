from rest_framework.permissions import BasePermission

class IsSuperAdminOrHasOrderPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        if user.role == user.Role.SUPER_ADMIN:
            return True  # Super Admins have full access

        if user.role == user.Role.ADMIN:
            try:
                perms = user.permissions
            except:
                return False

            action = view.action

            # Read operations
            if action in ['list', 'retrieve', 'get_by_status', 'status_options']:
                return perms.can_manage_orders

            # Update status custom action
            if action == 'update_status':
                # You can return True directly if you already checked each status permission when updating
                # OR check all update-related permissions (safer):
                return perms.can_manage_delivery_status


            # Delete or update
            if action in ['update', 'partial_update', 'destroy']:
                return perms.can_manage_orders

        return False
