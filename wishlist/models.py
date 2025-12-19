from django.conf import settings
from django.db import models
from product.models import Product

User = settings.AUTH_USER_MODEL

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")  # user cannot wishlist same product twice
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} → {self.product}"
