from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsSuperAdminOrHasProductPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == user.Role.SUPER_ADMIN:
            return True  # full access
        if user.role == user.Role.ADMIN:
            # Check product permissions based on action
            try:
                perms = user.permissions
            except:
                return False

            action = view.action
            if action == 'create':
                return perms.can_add_product
            elif action in ['update', 'partial_update']:
                return perms.can_edit_product
            elif action == 'destroy':
                return perms.can_delete_product
            elif action in ['list', 'retrieve']:
                return True  # allow read by default

        return False

class ImageViewPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if user.is_authenticated:
            return True