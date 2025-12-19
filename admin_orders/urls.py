# admin_orders/urls.py
from django.urls import path
from .views import AdminOrderList, AdminOrderDetail, AdminOrderStatus

urlpatterns = [
    path("admin_orders/", AdminOrderList.as_view(), name="admin-orders-list"),
    path("admin_orders/<int:pk>/", AdminOrderDetail.as_view(), name="admin-orders-detail"),
    path("admin_orders/<int:pk>/status/", AdminOrderStatus.as_view(), name="admin-orders-status"),
]
