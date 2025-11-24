# product/views.py
from rest_framework import viewsets, permissions, filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Product, Category, Size, ProductSize, Review
from .serializers import (
    ProductSerializer, CategorySerializer, SizeSerializer,
    ProductSizeSerializer, ReviewSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all().order_by("name")
    serializer_class = SizeSerializer
    permission_classes = [permissions.IsAdminUser]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    
    filterset_fields = {
        "category__slug": ["exact"],
        "category": ["exact"],
    }

    ordering_fields = ["created_at", "new_price"]
    search_fields = ["name", "category__name"]

class ProductSizeViewSet(viewsets.ModelViewSet):
    queryset = ProductSize.objects.all().select_related("product", "size")
    serializer_class = ProductSizeSerializer
    permission_classes = [permissions.IsAdminUser]

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("user", "product").all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["comment", "user__username", "product__name"]
    ordering_fields = ["created_at", "rating"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
