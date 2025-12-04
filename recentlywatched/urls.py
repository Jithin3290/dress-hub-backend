from django.urls import path
from .views import RecentlyWatchedViewSet

rv = RecentlyWatchedViewSet.as_view({
    "get": "list",
    "post": "create",
})

remove = RecentlyWatchedViewSet.as_view({
    "delete": "destroy",
})

urlpatterns = [
    path("recently-watched/", rv, name="recently-watched"),
    path("recently-watched/<int:pk>/", remove, name="recently-watched-remove"),
]
