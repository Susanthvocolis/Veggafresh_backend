from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import User, ModulePermission,OTP
from django.contrib.auth.hashers import make_password
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'mobile', 'email', 'role', 'first_name', 'last_name',
                  'profile_complete', 'date_of_birth', 'address']
        read_only_fields = ['role', 'profile_complete']

class OTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

class ProfileCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'date_of_birth', 'address']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['mobile'] = user.mobile
        token['profile_complete'] = user.profile_complete
        return token


#Employee


class ModulePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePermission
        exclude = ['id', 'employee']


class EmployeeSerializer(serializers.ModelSerializer):
    permissions = ModulePermissionSerializer(required=False)
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'mobile', 'password', 'address', 'role', 'permissions']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        permissions_data = validated_data.pop('permissions', {})

        # Auto-generate a unique username if not provided
        if 'username' not in validated_data or not validated_data['username']:
            validated_data['username'] = validated_data['mobile']

        user = User(**validated_data)
        user.role = User.Role.ADMIN
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        permissions_data = validated_data.pop('permissions', {})
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        ModulePermission.objects.update_or_create(employee=instance, defaults=permissions_data)
        return instance
