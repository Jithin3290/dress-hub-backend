from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Product, Category, Size, ProductSize, Review
from .serializers import (
    ProductSerializer, ProductMiniSerializer, CategorySerializer,
    SizeSerializer, ProductSizeSerializer, ReviewSerializer,
)
# use APIView 
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
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    queryset = Product.objects.all().select_related("category")
    serializer_class = ProductSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]

    filterset_fields = {
        "category__slug": ["exact"],
        "category": ["exact"],
    }
    ordering_fields = ["created_at", "new_price"]
    search_fields = ["name", "category__name"]

    @action(detail=False, methods=["get"])
    def mini(self, request):
        """
        Optional lightweight list for client components that only need a small product shape.
        GET /api/v1/products/mini/
        """
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = ProductMiniSerializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ProductSizeViewSet(viewsets.ModelViewSet):
    queryset = ProductSize.objects.all().select_related("product", "size")
    serializer_class = ProductSizeSerializer
    permission_classes = [permissions.IsAdminUser]


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("user", "product").all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["comment", "user__username", "product__name"]
    ordering_fields = ["created_at", "rating"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
