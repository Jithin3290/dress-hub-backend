from rest_framework import serializers
from .models import CartItem
from product.models import Product

class ProductBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "new_price", "image")

class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductBriefSerializer(source="product", read_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True)

    # accept size, return size, DO NOT validate
    size = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = CartItem
        fields = ("id", "product", "product_detail", "size", "quantity", "added_at")
        read_only_fields = ("id", "product_detail", "added_at")
