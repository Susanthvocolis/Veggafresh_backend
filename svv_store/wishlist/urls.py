from django.urls import path
from .views import WishlistListCreateAPIView, WishlistDeleteAPIView, WishlistClearAPIView

urlpatterns = [
    path('wishlist/', WishlistListCreateAPIView.as_view(), name='wishlist-list-create'),
    path('wishlist-remove/<int:product_id>/', WishlistDeleteAPIView.as_view(), name='wishlist-remove'),
    path('wishlist-clear/', WishlistClearAPIView.as_view(), name='wishlist-clear'),
]
