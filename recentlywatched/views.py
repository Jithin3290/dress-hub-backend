# recentlywatched/views.py
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import RecentlyWatched
from .serializers import RecentlyWatchedSerializer, RecentlyWatchedCreateSerializer, MAX_ITEMS
from product.models import Product

logger = logging.getLogger(__name__)

class RecentlyWatchedViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        qs = RecentlyWatched.objects.filter(user=request.user).select_related("product").order_by("-created_at")[:MAX_ITEMS]
        serializer = RecentlyWatchedSerializer(qs, many=True)
        return Response({"recently_watched": [item["product"] for item in serializer.data]})

    @transaction.atomic
    def create(self, request):
        try:
            serializer = RecentlyWatchedCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"detail": "Invalid payload", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            product_id = serializer.validated_data["product_id"]
            product = get_object_or_404(Product, pk=product_id)

            # Delete any existing entry for this product
            RecentlyWatched.objects.filter(user=request.user, product=product).delete()
            
            # Create new entry
            RecentlyWatched.objects.create(user=request.user, product=product)
            
            # Get all items for this user ordered by created_at
            items = RecentlyWatched.objects.filter(
                user=request.user
            ).order_by("-created_at")
            
            # Delete items beyond MAX_ITEMS
            # Using a subquery to avoid the LIMIT/OFFSET issue
            if items.count() > MAX_ITEMS:
                # Get the oldest item beyond MAX_ITEMS
                oldest_to_keep = items[MAX_ITEMS - 1].created_at
                # Delete items older than this
                RecentlyWatched.objects.filter(
                    user=request.user,
                    created_at__lt=oldest_to_keep
                ).delete()

            # Return the updated list
            qs = items[:MAX_ITEMS].select_related("product")
            out = RecentlyWatchedSerializer(qs, many=True)
            return Response(
                {"recently_watched": [item["product"] for item in out.data]},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.exception("Exception in recentlywatched.create")
            return Response(
                {"detail": "server error", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def destroy(self, request, pk=None):
        if pk is None:
            return Response({"detail": "Product id required."}, status=status.HTTP_400_BAD_REQUEST)
        RecentlyWatched.objects.filter(user=request.user, product_id=pk).delete()
        qs = RecentlyWatched.objects.filter(user=request.user).select_related("product").order_by("-created_at")[:MAX_ITEMS]
        out = RecentlyWatchedSerializer(qs, many=True)
        return Response({"recently_watched": [item["product"] for item in out.data]}, status=status.HTTP_200_OK)
