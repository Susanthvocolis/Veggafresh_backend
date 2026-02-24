from rest_framework import serializers
from users.models import User, ModulePermission
from users.serializers.permission_serializers import ModulePermissionSerializer


class EmployeeSerializer(serializers.ModelSerializer):
    permissions = ModulePermissionSerializer(required=False)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'mobile', 'password',
            'address', 'role', 'permissions'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        permissions_data = validated_data.pop('permissions', {})

        if 'username' not in validated_data or not validated_data.get('username'):
            validated_data['username'] = validated_data['mobile']

        user = User(**validated_data)
        user.role = User.Role.ADMIN
        user.set_password(password)
        user.save()

        # Create permissions
        if permissions_data:
            ModulePermission.objects.create(employee=user, **permissions_data)

        return user

    def update(self, instance, validated_data):
        permissions_data = validated_data.pop('permissions', {})
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if permissions_data:
            ModulePermission.objects.update_or_create(
                employee=instance, defaults=permissions_data
            )

        return instance
