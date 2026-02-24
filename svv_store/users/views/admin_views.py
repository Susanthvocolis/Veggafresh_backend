# user_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from users.models import User, ModulePermission
from users.serializers.permission_serializers import ModulePermissionSerializer


class AdminEmployeeLoginView(APIView):
    def post(self, request):
        username = request.data.get('username')  # Can be email or mobile
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if not user or user.role not in [User.Role.ADMIN, User.Role.SUPER_ADMIN, User.Role.ADMIN]:
            return Response(
                {'error': 'Invalid credentials or unauthorized access'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        user_data = {
            'id': user.id,
            'mobile': user.mobile,
            'email': user.email,
            'role': user.role,
            'is_superadmin': user.role == User.Role.SUPER_ADMIN,
        }

        # Include permissions only for employees
        if user.role == User.Role.ADMIN:
            try:
                permission = user.permissions  # reverse related_name
                user_data['permissions'] = ModulePermissionSerializer(permission).data
            except ModulePermission.DoesNotExist:
                user_data['permissions'] = {}  # or raise error if mandatory

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data
        })