from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
# serializers.py
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import serializers


from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'mobile', 'email', 'role', 'first_name', 'last_name',
                  'profile_complete', 'date_of_birth', 'address']
        read_only_fields = ['role', 'profile_complete']



class RequestOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True, trim_whitespace=True)

    def validate(self, data):
        identifier = data['identifier']
        if '@' in identifier:  # Email
            try:
                validate_email(identifier)
                data['identifier_type'] = 'email'
                data['identifier'] = identifier.lower()  # Normalize email
            except ValidationError:
                raise serializers.ValidationError({'identifier': 'Invalid email format'})
        else:  # Mobile
            if not re.match(r'^\+?[0-9]{10,15}$', identifier):
                raise serializers.ValidationError({'identifier': 'Invalid mobile number format'})
            data['identifier_type'] = 'mobile'
        return data


class VerifyOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True, trim_whitespace=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate(self, data):
        identifier = data['identifier']
        if '@' in identifier:  # Email
            try:
                validate_email(identifier)
                data['identifier_type'] = 'email'
                data['identifier'] = identifier.lower()  # Normalize email
            except ValidationError:
                raise serializers.ValidationError({'identifier': 'Invalid email format'})
        else:  # Mobile
            if not re.match(r'^\+?[0-9]{10,15}$', identifier):
                raise serializers.ValidationError({'identifier': 'Invalid mobile number format'})
            data['identifier_type'] = 'mobile'
        return data
class ProfileCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'date_of_birth', 'address']