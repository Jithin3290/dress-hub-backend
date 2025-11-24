# product/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Review, Product

@receiver([post_save, post_delete], sender=Review)
def update_product_rating_on_review_change(sender, instance, **kwargs):
    product = instance.product
    agg = product.reviews.aggregate(avg=Avg("rating"), count=Count("id"))
    avg = agg.get("avg") or 0.0
    count = agg.get("count") or 0
    # round to 1 decimal
    avg_rounded = round(float(avg) if avg else 0.0, 1)
    Product.objects.filter(pk=product.pk).update(avg_rating=avg_rounded, review_count=count)
