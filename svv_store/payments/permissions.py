from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsSuperAdminOrHasPaymentPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == user.Role.SUPER_ADMIN:
            return True  # full access
        if user.role == user.Role.ADMIN:
            action = getattr(view, 'action', None)
            if action is None:
                # APIView: derive action from HTTP method
                method = request.method.upper()
                action = {
                    'GET': 'list', 'POST': 'create',
                    'PUT': 'update', 'PATCH': 'partial_update', 'DELETE': 'destroy',
                }.get(method, 'list')

            if action == 'create':
                return True
            elif action in ['update', 'partial_update']:
                return False
            elif action == 'destroy':
                return False
            elif action in ['list', 'retrieve']:
                return True  # allow read by default

        return False
