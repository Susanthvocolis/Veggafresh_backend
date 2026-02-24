from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User, OTP
from users.serializers.permission_serializers import CustomTokenObtainPairSerializer
from users.serializers.user_serializers import ProfileCompletionSerializer, UserSerializer, RequestOTPSerializer, \
    VerifyOTPSerializer
from users.services import create_or_update_otp


class RequestOTPView(APIView):
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        identifier = serializer.validated_data['identifier']
        identifier_type = serializer.validated_data['identifier_type']
        email = identifier.strip().lower()
        # Normalize email
        if identifier_type == 'email':
            identifier = identifier.lower()
            user = User.objects.get(email__iexact=email)
            if not user:
                user = User.objects.create(email=identifier)
        else:  # mobile
            user = User.objects.get(mobile=identifier)
            if not user:
                user = User.objects.create(mobile=identifier)

        # Create OTP
        otp = create_or_update_otp(identifier, identifier_type, user)

        return Response({
            'message': f'OTP sent to {identifier_type} successfully',
            'identifier': identifier
        })


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        identifier = serializer.validated_data['identifier']
        otp = serializer.validated_data['otp']
        identifier_type = serializer.validated_data['identifier_type']

        if identifier_type == 'email':
            identifier = identifier.lower()
            lookup = {
                'otp': otp,
                'identifier__iexact': identifier,
                'is_used': False,
                'identifier_type': identifier_type
            }
        else:
            lookup = {
                'otp': otp,
                'identifier': identifier,
                'is_used': False,
                'identifier_type': identifier_type
            }

        try:
            otp_obj = OTP.objects.get(**lookup)

            if not otp_obj.is_valid():
                return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)

            # Mark OTP as used
            otp_obj.is_used = True
            otp_obj.save()

            # Get or update user
            if identifier_type == 'email':
                user = User.objects.get(email__iexact=identifier)
                if not user:
                    return Response({'error': 'Somthing is wrong please contact support'}, status=status.HTTP_400_BAD_REQUEST)
                if not user.is_email_verified:
                    user.is_email_verified = True
                    user.save()
            else:
                user = User.objects.filter(mobile=identifier).first()
                if not user:
                    user = User.objects.create(mobile=identifier)
                if not user.is_mobile_verified:
                    user.is_mobile_verified = True
                    user.save()

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'is_verified': True,
                'profile_complete': user.profile_complete
            })

        except OTP.DoesNotExist:
            return Response({'error': 'No OTP found for this identifier'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': f'error: {e}'}, status=status.HTTP_400_BAD_REQUEST)

class ProfileCompletionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = ProfileCompletionSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(profile_complete=True)
            return Response({'message': 'Profile completed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)