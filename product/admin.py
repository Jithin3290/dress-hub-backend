# product/admin.py
from django.contrib import admin
from .models import Product, Category, Review, Size, ProductSize

class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "new_price", "old_price", "avg_rating", "review_count", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductSizeInline]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__username", "comment")

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
