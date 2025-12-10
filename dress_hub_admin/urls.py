from django.urls import path
from . import views

urlpatterns = [
    path("users/", views.admin_users, name="admin_users"),
    path("products/", views.admin_products, name="admin_products"),
    path("orders/", views.admin_orders, name="admin_orders"),
]
