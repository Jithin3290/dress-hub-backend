
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from .models import Wishlist
from .serializers import WishlistSerializer
from product.models import Product

class WishlistListCreateAPIView(APIView):
    """
    GET: list current user's wishlist items
    POST: add a product to wishlist with payload { "product": <id> }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        qs = Wishlist.objects.filter(user=request.user).select_related("product")
        serializer = WishlistSerializer(qs, many=True, context={"request": request})
        # return as object to match prior contract: { id?, user?, items: [...] }
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        product_id = request.data.get("product")
        if product_id is None:
            return Response({"detail": "Missing 'product' in payload."}, status=status.HTTP_400_BAD_REQUEST)

        # validate product exists
        product = get_object_or_404(Product, pk=product_id)

        # prevent duplicates
        exists = Wishlist.objects.filter(user=request.user, product=product).exists()
        if exists:
            # return current wishlist so client stays authoritative
            qs = Wishlist.objects.filter(user=request.user).select_related("product")
            serializer = WishlistSerializer(qs, many=True, context={"request": request})
            return Response({"detail": "Already in wishlist", "items": serializer.data}, status=status.HTTP_200_OK)

        item = Wishlist.objects.create(user=request.user, product=product)

        # return updated wishlist
        qs = Wishlist.objects.filter(user=request.user).select_related("product")
        serializer = WishlistSerializer(qs, many=True, context={"request": request})
        return Response({"items": serializer.data}, status=status.HTTP_201_CREATED)


class WishlistDeleteAPIView(APIView):
    """
    DELETE /api/v1/wishlist/<int:pk>/  -> deletes that wishlist row (pk is wishlist item id)
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, format=None):
        obj = get_object_or_404(Wishlist, pk=pk)
        if obj.user != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

        obj.delete()
        qs = Wishlist.objects.filter(user=request.user).select_related("product")
        serializer = WishlistSerializer(qs, many=True, context={"request": request})
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)
