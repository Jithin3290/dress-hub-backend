from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from product.models import Product
from order.models import Order
from .serializers import (
    AdminUserSerializer,
    AdminProductSerializer,
    AdminOrderSerializer,
)

User = get_user_model()


# ---- USERS ----
@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_users(request):
    qs = User.objects.all().order_by("-id")
    return Response(AdminUserSerializer(qs, many=True).data)


# ---- PRODUCTS ----
@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_products(request):
    qs = Product.objects.all().order_by("-created_at")
    return Response(AdminProductSerializer(qs, many=True).data)


# ---- ORDERS ----
@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_orders(request):
    qs = Order.objects.all().order_by("-created_at").prefetch_related("items")
    return Response(AdminOrderSerializer(qs, many=True).data)
