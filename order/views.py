# orders/simple_views.py
import razorpay
from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from product.models import Product
from cart.models import CartItem
from .models import Order, OrderItem, Notification
from .serializers import (    
    CheckoutOrderSerializer,
    UserOrderSerializer,
    NotificationSerializer,
)

# simple client (uses keys from settings.py)
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_orders(request):
    """
    GET /api/orders/           -> list all user's orders
    GET /api/orders/?order_id= -> single order (optional)
    """
    order_id = request.query_params.get("order_id")
    if order_id:
        try:
            order = Order.objects.prefetch_related("items__product").get(
                id=order_id, user=request.user
            )
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserOrderSerializer(order).data)

    orders = Order.objects.filter(user=request.user).prefetch_related("items__product").order_by("-created_at")
    return Response(UserOrderSerializer(orders, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cod_checkout(request):
    """
    POST /api/orders/cod/
    Body: { "orders": [ { "product": id, "quantity": n, "size": "M", "shipping_address": "...", "phone": "..." }, ... ] }
    """
    orders_payload = request.data.get("orders")
    if not orders_payload:
        return Response({"error": "orders payload required"}, status=status.HTTP_400_BAD_REQUEST)

    # build products map
    prod_ids = [o["product"] for o in orders_payload]
    products = Product.objects.filter(id__in=prod_ids)
    product_map = {p.id: p for p in products}

    order_objects = []
    order_items_objects = []
    total_amount = 0

    # validate and construct
    for o in orders_payload:
        p = product_map.get(o["product"])
        if not p:
            return Response({"error": f"Product {o['product']} not found"}, status=status.HTTP_404_NOT_FOUND)
        qty = int(o.get("quantity", 1))
        if p.product_stock < qty:
            return Response({"error": f"Not enough stock for {p.name}"}, status=status.HTTP_400_BAD_REQUEST)

        price = p.price
        total_amount += price * qty

    # create DB records inside transaction
    with transaction.atomic():
        created_orders = []
        for o in orders_payload:
            p = product_map[o["product"]]
            qty = int(o.get("quantity", 1))
            price = p.price

            order = Order.objects.create(
                user=request.user,
                total_amount=price * qty,
                payment_status="PENDING",
                payment_method="COD",
                shipping_address=o.get("shipping_address", ""),
                phone=o.get("phone", ""),
            )

            OrderItem.objects.create(
                order=order,
                product=p,
                size=o.get("size", ""),
                quantity=qty,
                price=price,
            )

            # reduce stock
            Product.objects.filter(id=p.id).update(product_stock=F("product_stock") - qty)

            created_orders.append(order)

        # remove from cart for these products
        CartItem.objects.filter(user=request.user, product_id__in=prod_ids).delete()

    serializer = CheckoutOrderSerializer(created_orders, many=True)
    return Response({"message": "Orders placed (COD)", "orders": serializer.data, "total_amount": total_amount}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def razorpay_create_order(request):
    """
    POST /api/orders/razorpay-create/
    Body: { "orders": [ ... same as above ... ] }
    Returns: razorpay_order_id, key, amount (in paise)
    """
    orders_payload = request.data.get("orders")
    if not orders_payload:
        return Response({"error": "orders payload required"}, status=status.HTTP_400_BAD_REQUEST)

    # validate stock & calculate total
    prod_ids = [o["product"] for o in orders_payload]
    products = Product.objects.filter(id__in=prod_ids)
    product_map = {p.id: p for p in products}
    total = 0
    for o in orders_payload:
        p = product_map.get(o["product"])
        if not p:
            return Response({"error": f"Product {o['product']} not found"}, status=status.HTTP_404_NOT_FOUND)
        qty = int(o.get("quantity", 1))
        if p.product_stock < qty:
            return Response({"error": f"Not enough stock for {p.name}"}, status=status.HTTP_400_BAD_REQUEST)
        total += p.price * qty

    amount_paise = int(total * 100)
    razorpay_order = razorpay_client.order.create({"amount": amount_paise, "currency": "INR", "payment_capture": 1})

    return Response({
        "message": "Razorpay order created",
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": amount_paise,
        "currency": "INR",
        "orders_payload": orders_payload,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def razorpay_verify(request):
    """
    POST /api/orders/razorpay-verify/
    Body: {
      razorpay_payment_id, razorpay_order_id, razorpay_signature,
      orders_payload: [ ... ]
    }
    Verifies signature, creates orders+items, reduces stock, clears cart.
    """
    payment_id = request.data.get("razorpay_payment_id")
    order_id = request.data.get("razorpay_order_id")
    signature = request.data.get("razorpay_signature")
    orders_payload = request.data.get("orders_payload")

    if not all([payment_id, order_id, signature, orders_payload]):
        return Response({"error": "missing fields"}, status=status.HTTP_400_BAD_REQUEST)

    # verify signature
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "signature verification failed"}, status=status.HTTP_400_BAD_REQUEST)

    # normalize payload
    if isinstance(orders_payload, dict):
        orders_payload = [orders_payload]

    prod_ids = [o["product"] for o in orders_payload]
    products = Product.objects.filter(id__in=prod_ids)
    product_map = {p.id: p for p in products}

    created_orders = []
    total_amount = 0

    with transaction.atomic():
        for o in orders_payload:
            p = product_map.get(o["product"])
            if not p:
                return Response({"error": f"Product {o['product']} not found"}, status=status.HTTP_404_NOT_FOUND)
            qty = int(o.get("quantity", 1))
            if p.product_stock < qty:
                return Response({"error": f"Not enough stock for {p.name}"}, status=status.HTTP_400_BAD_REQUEST)

            price = p.price
            total_amount += price * qty

            order = Order.objects.create(
                user=request.user,
                total_amount=price * qty,
                payment_method="RAZORPAY",
                payment_status="PAID",
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                shipping_address=o.get("shipping_address", ""),
                phone=o.get("phone", ""),
            )

            OrderItem.objects.create(
                order=order,
                product=p,
                size=o.get("size", ""),
                quantity=qty,
                price=price,
            )

            # reduce stock
            Product.objects.filter(id=p.id).update(product_stock=F("product_stock") - qty)

        # clear cart entries for these products
        CartItem.objects.filter(user=request.user, product_id__in=prod_ids).delete()

    serializer = CheckoutOrderSerializer(created_orders, many=True)  # created_orders is empty here, but serializer below uses actual DB query if needed

    # fetch the newly created orders to return (simple approach)
    user_new_orders = Order.objects.filter(user=request.user).order_by("-created_at")[:len(orders_payload)]
    return Response({
        "message": "Payment verified and orders created",
        "total_amount": total_amount,
        "orders": CheckoutOrderSerializer(user_new_orders, many=True).data
    }, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_order_address(request, order_id):
    """
    PATCH /api/orders/<order_id>/address/
    Body: { "shipping_address": "..." }
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    shipping_address = request.data.get("shipping_address")
    if not shipping_address:
        return Response({"error": "shipping_address required"}, status=status.HTTP_400_BAD_REQUEST)

    order.shipping_address = shipping_address
    order.save()
    return Response(UserOrderSerializer(order).data, status=status.HTTP_200_OK)


# Simple notifications list + mark-as-read
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def notifications_view(request):
    if request.method == "GET":
        notes = Notification.objects.filter(user=request.user).order_by("-created_at")
        return Response(NotificationSerializer(notes, many=True).data)

    # PATCH: mark all as read (or accept {"id": <id>} to mark single)
    note_id = request.data.get("id")
    if note_id:
        Notification.objects.filter(id=note_id, user=request.user).update(read=True)
    else:
        Notification.objects.filter(user=request.user).update(read=True)
    return Response({"message": "notifications updated"}, status=status.HTTP_200_OK)
