from rest_framework.permissions import BasePermission


class IsSuperAdminOrHasBannerPermission(BasePermission):
    """
    Permission rules for the banners module:
    - SUPER_ADMIN  → full access (all CRUD)
    - ADMIN (employee) → checked against ModulePermission flags
        can_view_banner   → list, retrieve
        can_add_banner    → create
        can_edit_banner   → update, partial_update
        can_delete_banner → destroy
    - USER (end customer) → NO access at all (blocked entirely)
    - Unauthenticated    → NO access
    """

    def has_permission(self, request, view):
        user = request.user

        # Must be logged in
        if not user.is_authenticated:
            return False

        # Super admin bypasses all permission checks
        if user.role == user.Role.SUPER_ADMIN:
            return True

        # Admin (employee) — check granular banner permissions
        if user.role == user.Role.ADMIN:
            try:
                perms = user.permissions
            except Exception:
                return False

            action = view.action
            if action == 'create':
                return perms.can_add_banner
            if action in ['update', 'partial_update']:
                return perms.can_edit_banner
            if action == 'destroy':
                return perms.can_delete_banner
            if action in ['list', 'retrieve']:
                return perms.can_view_banner

        # USER role (end customers) and any other role → denied
        return False
