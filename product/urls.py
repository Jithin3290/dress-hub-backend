# product/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ProductViewSet, ReviewViewSet, CategoryViewSet,
    SizeViewSet, ProductSizeViewSet
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"reviews", ReviewViewSet, basename="review")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"sizes", SizeViewSet, basename="size")
router.register(r"product-sizes", ProductSizeViewSet, basename="productsize")

urlpatterns = [
    path("", include(router.urls)),
]
