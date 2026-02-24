from rest_framework import serializers
from users.models import ModulePermission
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class ModulePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePermission
        exclude = ['id', 'employee']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['mobile'] = user.mobile
        token['profile_complete'] = user.profile_complete
        return token