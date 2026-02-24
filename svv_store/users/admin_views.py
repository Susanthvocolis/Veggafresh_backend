# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User


class AdminLoginView(APIView):
    def post(self, request):
        username = request.data.get('username')  # Can be email or mobile
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if not user or user.role not in [User.Role.ADMIN, User.Role.SUPER_ADMIN]:
            return Response(
                {'error': 'Invalid credentials or unauthorized access'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'mobile': user.mobile,
                'email': user.email,
                'role': user.role,
                'is_superadmin': user.role == User.Role.SUPER_ADMIN
            }
        })