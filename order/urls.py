from django.urls import path
from .views import (
    user_orders,
    cod_checkout,
    razorpay_create_order,
    razorpay_verify,
    update_order_address,
)

urlpatterns = [
    path("my-orders/", user_orders, name="user_orders"),

    # COD checkout
    path("checkout/cod/", cod_checkout, name="cod_checkout"),

    # Razorpay checkout
    path("checkout/razorpay/create/", razorpay_create_order, name="razorpay_create_order"),
    path("checkout/razorpay/verify/", razorpay_verify, name="razorpay_verify"),

    # Update address
    path("<int:order_id>/update-address/", update_order_address, name="update_order_address"),

]
