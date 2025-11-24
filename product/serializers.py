# product/serializers.py
from rest_framework import serializers
from .models import Product, Category, Size, ProductSize, Review
from decimal import Decimal
from django.db.models import Avg

class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ["id", "name"]

class ProductSizeSerializer(serializers.ModelSerializer):
    size = SizeSerializer(read_only=True)
    size_id = serializers.PrimaryKeyRelatedField(queryset=Size.objects.all(), source="size", write_only=True)

    class Meta:
        model = ProductSize
        fields = ["id", "size", "size_id", "stock"]
        read_only_fields = ["id", "size"]

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    class Meta:
        model = Review
        fields = ["id", "product", "user", "user_id", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "user_id", "created_at", "updated_at"]

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be 1..5")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        validated_data["user"] = user
        return super().create(validated_data)

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source="category", write_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    sizes = ProductSizeSerializer(many=True, read_only=True)
    # cached fields
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=1, read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    # computed discount info
    discounted_price = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "category", "category_id",
            "image", "new_price", "old_price",
            "avg_rating", "review_count",
            "has_discount", "discounted_price", "discount_percent",
            "sizes", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "slug", "avg_rating", "review_count", "created_at", "updated_at"]

    def get_discounted_price(self, obj):
        return obj.discounted_price

    def get_discount_percent(self, obj):
        return obj.discount_percent

    def get_has_discount(self, obj):
        return obj.has_discount

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        img = data.get("image")
        if img and request and isinstance(img, str) and img.startswith("/"):
            data["image"] = request.build_absolute_uri(img)
        return data
