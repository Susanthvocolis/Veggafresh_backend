from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmailOrMobileModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None or password is None:
            return None

        try:
            # Check if input is email or mobile
            if '@' in username:
                user = UserModel.objects.get(email__iexact=username)
            else:
                user = UserModel.objects.get(mobile=username)
        except UserModel.DoesNotExist:
            # Run default password hasher to prevent timing attack
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None