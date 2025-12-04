from django.conf import settings
from django.db import models
from django.utils import timezone
from product.models import Product

User = settings.AUTH_USER_MODEL

class RecentlyWatched(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recently_watched_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="watched_by")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "product")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.product}"
