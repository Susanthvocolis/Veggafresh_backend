from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from .models import Wishlist
from products.models import Product
from .serializers import WishlistSerializer

CACHE_TIMEOUT = 60*5  # 1 minute for wishlist caching

class WishlistListCreateAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistSerializer

    def get_queryset(self):
        return Wishlist.objects.select_related('product').only(
            'id', 'product__id', 'product__name', 'product__slug', 'product__brand', 'created_at'
        ).filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        cache_key = f"user_wishlist_{request.user.id}"
        wishlist_data = cache.get(cache_key)

        if not wishlist_data:
            queryset = self.get_queryset().iterator()  # efficient memory
            serializer = self.get_serializer(queryset, many=True)
            wishlist_data = serializer.data
            cache.set(cache_key, wishlist_data, CACHE_TIMEOUT)

        return Response(wishlist_data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({"error": "Product ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not Product.objects.only('id').filter(id=product_id).exists():
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        wishlist_obj, created = Wishlist.objects.get_or_create(
            user=request.user,
            product_id=product_id
        )

        if not created:
            return Response({"message": "Already in your wishlist."}, status=status.HTTP_200_OK)

        # Clear cache after addition
        cache.delete(f"user_wishlist_{request.user.id}")

        serializer = self.get_serializer(wishlist_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class WishlistDeleteAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        try:
            wishlist_item = Wishlist.objects.only('id').get(user=request.user, product_id=product_id)
        except Wishlist.DoesNotExist:
            return Response({"error": "Product not in wishlist."}, status=status.HTTP_404_NOT_FOUND)

        wishlist_item.delete()

        # Clear cache after deletion
        cache.delete(f"user_wishlist_{request.user.id}")

        return Response({"message": "Product removed from wishlist."}, status=status.HTTP_204_NO_CONTENT)


class WishlistClearAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        wishlist_qs = Wishlist.objects.filter(user=request.user)

        if not wishlist_qs.exists():
            return Response({"message": "Your wishlist is already empty."}, status=status.HTTP_200_OK)

        wishlist_qs.delete()

        # Clear cache after deletion
        cache.delete(f"user_wishlist_{request.user.id}")

        return Response({"message": "All products removed from wishlist."}, status=status.HTTP_204_NO_CONTENT)
