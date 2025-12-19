
from django.urls import path
from .views import CartListCreateAPIView, CartItemDetailAPIView

urlpatterns = [
    path("", CartListCreateAPIView.as_view(), name="cart-list-create"),
    path("<int:pk>/", CartItemDetailAPIView.as_view(), name="cart-item-detail"),
]
