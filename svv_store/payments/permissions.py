from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsSuperAdminOrHasPaymentPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == user.Role.SUPER_ADMIN:
            return True  # full access
        if user.role == user.Role.ADMIN:

            action = view.action
            if action == 'create':
                return True
            elif action in ['update', 'partial_update']:
                return False
            elif action == 'destroy':
                return False
            elif action in ['list', 'retrieve','update', 'partial_update']:
                return True  # allow read by default

        return False
