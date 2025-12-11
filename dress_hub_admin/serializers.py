from rest_framework import serializers
from django.contrib.auth import get_user_model
from product.models import Product
from order.models import Order, OrderItem
from product.serializers import CategorySerializer
User = get_user_model()


# ---- USERS ----
class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id","name","email","phone_number","profile_picture","is_banned","is_staff","is_superuser")
# ---- PRODUCTS ----
class AdminProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "new_price", "old_price", "image", "category"]
# ---- ORDER ITEMS (nested) ----
class AdminOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "size", "price"]
# ---- ORDERS ----
class AdminOrderSerializer(serializers.ModelSerializer):
    items = AdminOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "total_amount",
            "payment_status",
            "order_status",
            "shipping_address",
            "phone",
            "created_at",
            "items",
        ]
