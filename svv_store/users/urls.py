from django.urls import path
from users.views.admin_views import AdminEmployeeLoginView
from users.views.employee_views import EmployeeListView, EmployeeCreateView, EmployeeDetailUpdateDeleteView, \
    UsersListView
from users.views.user_views import RequestOTPView, VerifyOTPView, CustomTokenObtainPairView, ProfileCompletionView, \
    UserDetailsView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [


    # Login APIs
    path('login/', AdminEmployeeLoginView.as_view(), name='admin-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Admin APIs
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('all-users/', UsersListView.as_view(), name='employee-list'),
    path('employees/create/', EmployeeCreateView.as_view(), name='employee-create'),
    path('employees/<int:id>/', EmployeeDetailUpdateDeleteView.as_view(), name='employee-detail-update-delete'),
    # User APIs
    path('request-otp/', RequestOTPView.as_view(), name='request_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('complete-profile/', ProfileCompletionView.as_view(), name='complete_profile'),
    path('me/', UserDetailsView.as_view(), name='user_details'),
]