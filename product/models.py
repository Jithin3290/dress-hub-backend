from django.db import models
from django.conf import settings
from django.utils.text import slugify
from decimal import Decimal, ROUND_HALF_UP

User = settings.AUTH_USER_MODEL

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Size(models.Model):
    """
    Canonical size list (S, M, L, XL, 28, 30, etc)
    """
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # cached rating fields (kept in sync by signals)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # auto-generate slug if not provided
        if not self.slug:
            base = slugify(self.name)[:200]
            slug = base
            i = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def has_discount(self):
        return bool(self.old_price and (self.old_price > self.new_price))

    @property
    def discount_amount(self):
        if not self.has_discount:
            return Decimal("0.00")
        return (Decimal(self.old_price) - Decimal(self.new_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def discount_percent(self):
        if not self.has_discount:
            return Decimal("0.0")
        try:
            percent = (Decimal(self.discount_amount) / Decimal(self.old_price)) * Decimal(100)
            return percent.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.0")

    @property
    def discounted_price(self):
        # For clarity — same as new_price. kept for API convenience.
        return self.new_price


class ProductSize(models.Model):
    """
    Per-product, per-size stock entry.
    Example: Product A, Size M, stock 10
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sizes")
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    stock = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("product", "size")

    def __str__(self):
        return f"{self.product.name} - {self.size.name} ({self.stock})"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="product_reviews")
    rating = models.PositiveSmallIntegerField()  # 1..5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("product", "user")

    def __str__(self):
        return f"Review {self.rating} by {self.user} for {self.product}"