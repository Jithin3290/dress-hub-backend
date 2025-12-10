# admin_orders/serializers.py
from rest_framework import serializers
from order.models import Order, OrderItem, Notification
from django.contrib.auth import get_user_model

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_image = serializers.ImageField(source="product.image", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_image",
            "size",
            "quantity",
            "price",
        ]


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email"]


class AdminOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = UserSummarySerializer(read_only=True)

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
            "updated_at",
            "items",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at", "items"]
