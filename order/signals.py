from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Order

@receiver(pre_save, sender=Order)
def order_pre_save(sender, instance, **kwargs):
    if instance.pk:
        old = Order.objects.get(pk=instance.pk)
        instance._old_status = old.order_status
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    if created:
        return

    old_status = getattr(instance, "_old_status", None)
    new_status = instance.order_status

    if old_status == new_status:
        return

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{instance.user.id}",
        {
            "type": "send_notification", # Handler method name in consumer
            "data": {
                "order_id": instance.id,
                "status": new_status,
                "message": f"Your order #{instance.id} is now {new_status}"
            }
        }
    )

    print("WS notification sent")
