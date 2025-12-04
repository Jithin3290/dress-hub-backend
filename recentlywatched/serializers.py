# recentlywatched/serializers.py
from rest_framework import serializers
from .models import RecentlyWatched
from product.models import Product

MAX_ITEMS = 4

class ProductMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "slug", "image", "new_price", "old_price")

class RecentlyWatchedSerializer(serializers.ModelSerializer):
    product = ProductMiniSerializer(read_only=True)

    class Meta:
        model = RecentlyWatched
        fields = ("product", "created_at")

class RecentlyWatchedCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Product not found.")
        return value
