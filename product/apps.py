# product/apps.py
from django.apps import AppConfig

class ProductConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "product"

    def ready(self):
        # import signals so they register
        import product.signals  # noqa
