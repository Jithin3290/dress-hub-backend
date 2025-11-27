from django.conf import settings
from django.db import models
from django.utils import timezone
from product.models import Product  # adjust if product app name differs

User = settings.AUTH_USER_MODEL

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "product")
        ordering = ("-added_at",)

    def __str__(self):
        return f"{self.user_id} - {self.product_id} x{self.quantity}"

