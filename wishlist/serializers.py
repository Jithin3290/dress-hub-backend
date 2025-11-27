from rest_framework import serializers
from .models import Wishlist
from product.models import Product

class ProductBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        # adjust fields to match your Product model
        fields = ("id", "name", "new_price", "old_price", "image")

class WishlistSerializer(serializers.ModelSerializer):
    product_detail = ProductBriefSerializer(source="product", read_only=True)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True
    )

    class Meta:
        model = Wishlist
        fields = ("id", "product", "product_detail", "created_at")
        read_only_fields = ("id", "product_detail", "created_at")
