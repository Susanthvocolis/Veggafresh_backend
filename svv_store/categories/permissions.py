from rest_framework.permissions import BasePermission, SAFE_METHODS
class IsSuperAdminOrHasCategoryPermission(BasePermission):
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

            action = view.action

            if action == 'create':
                return perms.can_add_category
            elif action in ['update', 'partial_update']:
                return perms.can_edit_category
            elif action == 'destroy':
                return perms.can_delete_category
            elif action in ['list', 'retrieve']:
                return True

        return False
