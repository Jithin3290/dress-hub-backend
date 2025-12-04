from rest_framework import serializers
from .models import Product, Category, Size, ProductSize, Review

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ("id", "name")


class ProductMiniSerializer(serializers.ModelSerializer):
    # minimal product shape for lists, recently-watched, cart previews
    category = serializers.CharField(source="category.name", read_only=True)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "slug", "image", "new_price", "old_price", "category")


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    sizes = serializers.SerializerMethodField()
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=1, read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "image", "new_price", "old_price",
            "has_discount", "discount_amount", "discount_percent", "discounted_price",
            "avg_rating", "review_count", "category", "sizes", "created_at", "updated_at",
        )
        read_only_fields = ("avg_rating", "review_count", "created_at", "updated_at")

    def get_sizes(self, obj):
        # return available sizes and stock (small list)
        qs = obj.sizes.all().select_related("size")
        return [{"size": s.size.name, "stock": s.stock} for s in qs]


class ProductSizeSerializer(serializers.ModelSerializer):
    product = ProductMiniSerializer(read_only=True)
    size = SizeSerializer(read_only=True)

    class Meta:
        model = ProductSize
        fields = ("id", "product", "size", "stock")


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ("id", "product", "user", "rating", "comment", "created_at")
        read_only_fields = ("user", "created_at")
