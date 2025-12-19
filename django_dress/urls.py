"""
URL configuration for django_dress project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/user/',include('user.urls')),
    path("api/v1/", include("product.urls")),
    path("api/v1/wishlist/", include("wishlist.urls")),
    path("api/v1/cart/", include("cart.urls")),
    path("api/v1/order/", include("order.urls")),
    path("api/v1/admin/", include("dress_hub_admin.urls")),
    path("api/v1/admin/", include("admin_orders.urls")),
    path("api/v1/admin/", include("admin_products.urls")),
    path("api/v1/admin/", include("admin_user.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),#OpenAPI JSON/YAML
    path("api/v1/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),#interactive Swagger UI
    path("api/v1/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),#clean docs via ReDoc
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
