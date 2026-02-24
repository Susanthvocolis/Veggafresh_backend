"""
URL configuration for svv_store project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from orders.views.report_export import SecureFileDownloadView
from svv_store import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('users.urls')),
    path('api/v1/', include('categories.urls')),
    path('api/v1/', include('products.urls')),
    path('api/v1/', include('orders.urls')),
    path('api/v1/', include('payments.urls')),
    path('api/v1/', include('cart.urls')),
    path('api/v1/', include('address.urls')),
    path('api/v1/', include('wishlist.urls')),
    path('download/', SecureFileDownloadView.as_view(), name='secure_download'),
]
# Add this at the end of the file, outside of urlpatterns
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)