# users/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm
from .models import User

# For admin login
class AdminEmailMobileLoginForm(AuthenticationForm):
    username = forms.CharField(label="Email or Mobile")

# For user editing in admin
class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'