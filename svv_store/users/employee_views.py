from rest_framework import generics, permissions
from .models import User
from .serializers import EmployeeSerializer
from .permissions import IsSuperAdmin


class EmployeeListView(generics.ListAPIView):
    queryset = User.objects.filter(role=User.Role.ADMIN)
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]


class EmployeeCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
