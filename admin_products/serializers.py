# admin_products/serializers.py
from rest_framework import serializers
from django.db import transaction
from product.models import Product, ProductSize, Size, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ["id", "name"]


class ProductSizeSerializer(serializers.ModelSerializer):
    size_name = serializers.CharField(source="size.name", read_only=True)

    class Meta:
        model = ProductSize
        fields = ["id", "size", "size_name", "stock"]


class AdminProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, source="category"
    )

    # accept uploaded file for image
    image = serializers.ImageField(required=False, allow_null=True, write_only=True)
    # return absolute image url to frontend
    image_url = serializers.SerializerMethodField(read_only=True)

    sizes = ProductSizeSerializer(many=True, read_only=True)

    # sizes_input: list of string tokens like ["S","M","XL"]
    sizes_input = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    stock = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "image", "image_url",
            "new_price", "old_price", "stock",
            "category", "category_id",
            "sizes", "sizes_input",
            "created_at", "updated_at",
        ]
        read_only_fields = ("slug", "created_at", "updated_at", "sizes", "image_url")
    # ---------------- VALIDATION ----------------

    def validate_new_price(self, value):
        if value < 0:
            raise serializers.ValidationError("New price cannot be negative")
        return value

    def validate_old_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Old price cannot be negative")
        return value


    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        try:
            return request.build_absolute_uri(obj.image.url)
        except Exception:
            return obj.image.url

    def _normalize_size_name(self, raw: str) -> str:
        s = (raw or "").strip()
        if not s:
            return ""
        # prefer uppercase for textual sizes, keep numeric tokens as-is but uppercase non-alpha
        return s.upper()

    def _ensure_size_objects(self, size_names):
        """
        Ensure Size rows exist for the given normalized names.
        Returns mapping name->Size instance.
        """
        result = {}
        for name in size_names:
            if not name:
                continue
            size_obj, _ = Size.objects.get_or_create(name=name)
            result[name] = size_obj
        return result

    def _replace_sizes(self, product, size_names, stock_value):
        """
        Delete existing ProductSize rows for product and create new ones
        with given stock_value for each size in size_names.
        """
        normalized = [self._normalize_size_name(n) for n in size_names if n and str(n).strip()]
        # dedupe preserving order
        seen = set()
        dedup = []
        for n in normalized:
            if n in seen:
                continue
            seen.add(n)
            dedup.append(n)

        size_map = self._ensure_size_objects(dedup)

        ProductSize.objects.filter(product=product).delete()
        for name in dedup:
            sz = size_map.get(name)
            if sz:
                ProductSize.objects.create(product=product, size=sz, stock=int(stock_value or 0))

    @transaction.atomic
    def create(self, validated_data):
        sizes_input = validated_data.pop("sizes_input", None)
        stock_val = validated_data.pop("stock", None)
        product = super().create(validated_data)
        if sizes_input:
            self._replace_sizes(product, sizes_input, stock_val or 0)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        sizes_input = validated_data.pop("sizes_input", None)
        stock_val = validated_data.pop("stock", None)
        product = super().update(instance, validated_data)
        if sizes_input is not None:
            # if sizes_input explicitly provided, replace sizes; otherwise leave sizes untouched
            self._replace_sizes(product, sizes_input, stock_val if stock_val is not None else (product.sizes.first().stock if product.sizes.exists() else 0))
        return product
