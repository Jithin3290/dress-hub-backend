# orders/serializers.py
from rest_framework import serializers
from product.serializers import ProductSerializer
from product.models import Product

from .models import Order, OrderItem, Notification


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "size", "quantity", "price"]


class BaseOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "total_amount",
            "payment_status",
            "payment_method",
            "order_status",
            "tracking_id",
            "delivery_date",
            "shipping_address",
            "phone",
            "items",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "total_amount",
            "payment_status",
            "order_status",
            "tracking_id",
            "delivery_date",
            "created_at",
        ]


# Views expect these exact names
class CheckoutOrderSerializer(BaseOrderSerializer):
    pass


class UserOrderSerializer(BaseOrderSerializer):
    pass


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "message", "created_at", "read"]
        read_only_fields = ["id", "message", "created_at"]
