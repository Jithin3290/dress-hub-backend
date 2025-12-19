# admin_products/urls.py
from django.urls import path
from .views import AdminProductListCreate, AdminProductDetail, AdminCategoryList, AdminSizeList

urlpatterns = [
    path("admin_products/", AdminProductListCreate.as_view(), name="admin-products-list"),
    path("admin_products/<int:pk>/", AdminProductDetail.as_view(), name="admin-products-detail"),
    path("categories/", AdminCategoryList.as_view(), name="admin-categories-list"),
    path("sizes/", AdminSizeList.as_view(), name="admin-sizes-list"),
]
