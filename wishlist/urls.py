from django.urls import path
from .views import WishlistListCreateAPIView, WishlistDeleteAPIView

urlpatterns = [
    path("", WishlistListCreateAPIView.as_view(), name="wishlist-list-create"),
    path("<int:pk>/", WishlistDeleteAPIView.as_view(), name="wishlist-delete"),
]