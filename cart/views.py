from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from .models import CartItem
from .serializers import CartItemSerializer
from product.models import Product


class CartListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        qs = CartItem.objects.filter(user=request.user).select_related("product")
        serializer = CartItemSerializer(qs, many=True, context={"request": request})
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        """
        Expected payload:
        {
            "product": <id>,
            "quantity": <int>,
            "size": "XL"
        }
        """
        product_id = request.data.get("product")
        qty = int(request.data.get("quantity", 1))
        size = request.data.get("size")  # accept as-is, no validation

        if not product_id:
            return Response({"detail": "Missing 'product' in payload."},
                            status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, pk=product_id)

        # GET OR CREATE by (user, product, size)
        item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            size=size,
            defaults={"quantity": qty}
        )

        if not created:
            # Add to existing quantity
            item.quantity += qty
            item.save()

        qs = CartItem.objects.filter(user=request.user).select_related("product")
        serializer = CartItemSerializer(qs, many=True, context={"request": request})

        return Response(
            {"items": serializer.data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class CartItemDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, format=None):
        """ Update quantity only. """
        obj = get_object_or_404(CartItem, pk=pk, user=request.user)

        qty = request.data.get("quantity")
        if qty is None:
            return Response({"detail": "Missing 'quantity' in payload."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            qty = int(qty)
            if qty < 1:
                return Response({"detail": "Quantity must be >= 1"},
                                status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid 'quantity' value"},
                            status=status.HTTP_400_BAD_REQUEST)

        obj.quantity = qty
        obj.save()

        qs = CartItem.objects.filter(user=request.user).select_related("product")
        serializer = CartItemSerializer(qs, many=True, context={"request": request})
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)

    def delete(self, request, pk, format=None):
        obj = get_object_or_404(CartItem, pk=pk, user=request.user)
        obj.delete()

        qs = CartItem.objects.filter(user=request.user).select_related("product")
        serializer = CartItemSerializer(qs, many=True, context={"request": request})
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)
