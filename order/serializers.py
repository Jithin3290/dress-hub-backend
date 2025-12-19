# orders/serializers.py
from rest_framework import serializers
from product.serializers import ProductSerializer
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
            "razorpay_order_id",
            "razorpay_payment_id",
            "shipping_address",
            "phone",
            "items",
            "created_at",
            "order_status",
        ]
        read_only_fields = fields  # all are read-only for output only


class CheckoutOrderSerializer(BaseOrderSerializer):
    pass


class UserOrderSerializer(BaseOrderSerializer):
    pass

