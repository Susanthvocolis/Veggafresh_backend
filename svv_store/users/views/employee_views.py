from rest_framework import generics, permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from users.models import User
from users.permissions import IsSuperAdmin
from users.serializers.employee_serializers import EmployeeSerializer
from users.serializers.user_serializers import UserSerializer


class EmployeeListView(generics.ListAPIView):
    queryset = User.objects.filter(role=User.Role.ADMIN)
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

class UsersListView(generics.ListAPIView):
    queryset = User.objects.filter(role=User.Role.USER)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

class EmployeeCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

class EmployeeDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.filter(role=User.Role.ADMIN)
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    lookup_field = 'id'
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({'detail': 'Employee deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)