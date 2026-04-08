from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response

from users.models import User
from .models import Address
from .serializers import AddressSerializer, AdminAddressSerializer


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.role in (User.Role.SUPER_ADMIN, User.Role.ADMIN)


# ---------------------------------------------------------------------------
# User APIs
# ---------------------------------------------------------------------------

class AddressViewSet(viewsets.ModelViewSet):
    """
    User-facing address CRUD.

    GET    /api/v1/address/              — list my addresses
    POST   /api/v1/address/              — create address
    GET    /api/v1/address/<id>/         — retrieve address
    PATCH  /api/v1/address/<id>/         — update address
    DELETE /api/v1/address/<id>/         — delete address
    PATCH  /api/v1/address/<id>/set-default/ — mark as default
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

    def _clear_default(self):
        Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)

    def perform_create(self, serializer):
        if serializer.validated_data.get('is_default'):
            self._clear_default()
        # If this is the user's first address, auto-set as default
        is_first = not Address.objects.filter(user=self.request.user).exists()
        serializer.save(user=self.request.user, is_default=serializer.validated_data.get('is_default', is_first))

    def perform_update(self, serializer):
        if serializer.validated_data.get('is_default'):
            self._clear_default()
        serializer.save()

    def perform_destroy(self, instance):
        was_default = instance.is_default
        instance.delete()
        # Auto-assign default to the next most-recent address if needed
        if was_default:
            next_address = Address.objects.filter(user=self.request.user).order_by('-created_at').first()
            if next_address:
                next_address.is_default = True
                next_address.save(update_fields=['is_default'])

    @action(detail=True, methods=['patch'], url_path='set-default')
    def set_default(self, _request, pk=None):
        address = self.get_object()
        self._clear_default()
        address.is_default = True
        address.save(update_fields=['is_default'])
        return Response(AddressSerializer(address).data)


# ---------------------------------------------------------------------------
# Admin APIs
# ---------------------------------------------------------------------------

class AdminAddressViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-facing address APIs (read + delete only).

    GET    /api/v1/admin/addresses/              — list all addresses (filter: ?user_id=, ?city=, ?pincode=)
    GET    /api/v1/admin/addresses/<id>/         — retrieve any address
    DELETE /api/v1/admin/addresses/<id>/         — delete any address
    """
    permission_classes = [IsSuperAdminOrAdmin]
    serializer_class = AdminAddressSerializer
    http_method_names = ['get', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = Address.objects.select_related('user').order_by('-created_at')
        user_id = self.request.query_params.get('user_id')
        city = self.request.query_params.get('city')
        pincode = self.request.query_params.get('pincode')
        if user_id:
            qs = qs.filter(user_id=user_id)
        if city:
            qs = qs.filter(city__icontains=city)
        if pincode:
            qs = qs.filter(pincode=pincode)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        was_default = instance.is_default
        user = instance.user
        instance.delete()
        if was_default:
            next_address = Address.objects.filter(user=user).order_by('-created_at').first()
            if next_address:
                next_address.is_default = True
                next_address.save(update_fields=['is_default'])
        return Response({'message': 'Address deleted successfully.'}, status=status.HTTP_200_OK)
