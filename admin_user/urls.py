from django.urls import path
from .views import UserListAPIView, UserDetailAPIView, ToggleBanAPIView

urlpatterns = [
    path("admin_user/", UserListAPIView.as_view(), name="admin-user-list"),
    path("admin_user/<int:pk>/", UserDetailAPIView.as_view(), name="admin-user-detail"),
    path("admin_user/<int:pk>/toggle-ban/", ToggleBanAPIView.as_view(), name="admin-user-toggle-ban"),
]
