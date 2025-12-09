# orders/simple_views.py
import razorpay
from product.models import Product, ProductSize

from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import hmac, hashlib, traceback
from django.db import transaction, IntegrityError
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


# COD checkout (safe field handling)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cod_checkout(request):
    orders_payload = request.data.get("orders")
    if not orders_payload:
        return Response({"error": "orders payload required"}, status=status.HTTP_400_BAD_REQUEST)

    prod_ids = [o["product"] for o in orders_payload]
    products = Product.objects.filter(id__in=prod_ids)
    product_map = {p.id: p for p in products}

    created_orders = []
    total_amount = 0

    order_field_names = {f.name for f in Order._meta.get_fields()}

    with transaction.atomic():
        for o in orders_payload:
            p = product_map.get(o["product"])
            if not p:
                return Response({"error": f"Product {o['product']} not found"}, status=status.HTTP_404_NOT_FOUND)

            qty = int(o.get("quantity", 1))
            price = getattr(p, "new_price", None)
            if price is None:
                price = getattr(p, "price", None) or getattr(p, "old_price", 0)
            total_amount += price * qty

            # build order instance without optional fields
            order = Order(
                user=request.user,
                total_amount=price * qty,
                shipping_address=o.get("shipping_address", ""),
                phone=o.get("phone", ""),
            )

            # only set optional fields if they exist on the model
            if "payment_status" in order_field_names:
                setattr(order, "payment_status", "PENDING")
            if "payment_method" in order_field_names:
                setattr(order, "payment_method", "COD")

            order.save()
            # use bulk create
            OrderItem.objects.create(
                order=order,
                product=p,
                size=o.get("size", ""),
                quantity=qty,
                price=price,
            )

            created_orders.append(order)

        CartItem.objects.filter(user=request.user, product_id__in=prod_ids).delete()

    serializer = CheckoutOrderSerializer(created_orders, many=True)
    return Response({"message": "Orders placed (COD)", "orders": serializer.data, "total_amount": total_amount}, status=status.HTTP_201_CREATED)


# razorpay create (no stock checks)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def razorpay_create_order(request):
    """
    POST /api/v1/order/checkout/razorpay/create/
    Body: { "orders": [ ... ] }
    Returns: razorpay_order_id, key, amount (in paise)
    """
    orders_payload = request.data.get("orders")
    if not orders_payload:
        return Response({"error": "orders payload required"}, status=status.HTTP_400_BAD_REQUEST)

    # build products map and calculate total (no stock checks)
    prod_ids = [o["product"] for o in orders_payload]
    products = Product.objects.filter(id__in=prod_ids)
    product_map = {p.id: p for p in products}

    total = 0
    for o in orders_payload:
        p = product_map.get(o["product"])
        if not p:
            return Response({"error": f"Product {o['product']} not found"}, status=status.HTTP_404_NOT_FOUND)

        qty = int(o.get("quantity", 1))

        # use new_price if exists, else price, else old_price
        price = getattr(p, "new_price", None)
        if price is None:
            price = getattr(p, "price", None) or getattr(p, "old_price", 0)

        total += price * qty

    amount_paise = int(total * 100)

    razorpay_order = razorpay_client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1
    })

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
    try:
        payment_id = request.data.get("razorpay_payment_id")
        order_id = request.data.get("razorpay_order_id")
        signature = request.data.get("razorpay_signature")
        orders_payload = request.data.get("orders_payload")
        client_amount = request.data.get("amount", None)

        if not all([payment_id, order_id, signature, orders_payload]):
            return Response({"error": "missing fields"}, status=status.HTTP_400_BAD_REQUEST)

        # normalize orders_payload
        if isinstance(orders_payload, dict):
            orders_payload = [orders_payload]
        if not isinstance(orders_payload, list) or len(orders_payload) == 0:
            return Response({"error": "orders_payload must be a non-empty list or object"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch products, map by id
        prod_ids = []
        for o in orders_payload:
            try:
                pid = int(o.get("product"))
            except Exception:
                return Response({"error": f"invalid product id in payload: {o.get('product')}"}, status=status.HTTP_400_BAD_REQUEST)
            prod_ids.append(pid)

        products = Product.objects.filter(id__in=prod_ids)
        product_map = {p.id: p for p in products}

        # compute expected total in rupees (Decimal)
        expected_total = Decimal("0.00")
        for o in orders_payload:
            pid = int(o.get("product"))
            p = product_map.get(pid)
            if not p:
                return Response({"error": f"Product {pid} not found"}, status=status.HTTP_404_NOT_FOUND)

            qty = int(o.get("quantity", 1))
            price = getattr(p, "new_price", None)
            if price is None:
                price = getattr(p, "price", None) or getattr(p, "old_price", 0)

            try:
                price_num = Decimal(str(price))
            except Exception:
                price_num = Decimal("0.00")

            expected_total += price_num * qty

        # interpret client_amount if provided (try to detect paise vs rupees)
        client_amount_rupees = None
        if client_amount is not None:
            try:
                client_amount_int = int(client_amount)
                if client_amount_int > (expected_total * Decimal(10)):
                    client_amount_rupees = Decimal(client_amount_int) / Decimal(100)
                else:
                    client_amount_rupees = Decimal(str(client_amount))
            except Exception:
                try:
                    client_amount_rupees = Decimal(str(client_amount))
                except Exception:
                    client_amount_rupees = None

        if client_amount_rupees is not None:
            if round(client_amount_rupees, 2) != round(expected_total, 2):
                return Response({
                    "error": "amount_mismatch",
                    "message": "Client amount does not match server computed total",
                    "client_amount": str(client_amount_rupees),
                    "server_total": str(expected_total)
                }, status=status.HTTP_400_BAD_REQUEST)

        # verify signature using razorpay utility
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "signature verification failed"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            traceback.print_exc()
            return Response({"error": "signature verification error"}, status=status.HTTP_400_BAD_REQUEST)

        # Build order kwargs only with real model fields
        order_field_names = {f.name for f in Order._meta.get_fields()}
        order_kwargs = {"user": request.user}
        if "total_amount" in order_field_names:
            order_kwargs["total_amount"] = expected_total
        if "payment_method" in order_field_names:
            order_kwargs["payment_method"] = "RAZORPAY"
        if "payment_status" in order_field_names:
            order_kwargs["payment_status"] = "PAID"
        if "razorpay_order_id" in order_field_names:
            order_kwargs["razorpay_order_id"] = order_id
        if "razorpay_payment_id" in order_field_names:
            order_kwargs["razorpay_payment_id"] = payment_id

        first = orders_payload[0] if len(orders_payload) else {}
        if "shipping_address" in order_field_names and first.get("shipping_address"):
            order_kwargs["shipping_address"] = first.get("shipping_address")
        if "phone" in order_field_names and first.get("phone"):
            order_kwargs["phone"] = first.get("phone")

        # Create one Order and its OrderItems inside a transaction
        try:
            with transaction.atomic():
                # 1) Lock all ProductSize rows needed and validate stock
                # We'll collect tuples (product, size_name, qty) so we can create items after validation.
                validation_items = []
                for o in orders_payload:
                    pid = int(o.get("product"))
                    p = product_map.get(pid)
                    qty = int(o.get("quantity", 1))
                    size_name = o.get("size", "")
                    if not size_name:
                        return Response({"error": f"size required for product {pid}"}, status=status.HTTP_400_BAD_REQUEST)

                    try:
                        ps = ProductSize.objects.select_for_update().get(product=p, size__name=size_name)
                    except ProductSize.DoesNotExist:
                        return Response({"error": f"Size '{size_name}' not available for product {pid}"}, status=status.HTTP_400_BAD_REQUEST)

                    if ps.stock < qty:
                        return Response({"error": f"Insufficient stock for {p.name} size {size_name}"}, status=status.HTTP_400_BAD_REQUEST)

                    validation_items.append((p, size_name, qty))

                # 2) Create Order
                order = Order.objects.create(**order_kwargs)

                # 3) Create OrderItems and decrement stock (atomically using F)
                for p, size_name, qty in validation_items:
                    price = getattr(p, "new_price", None)
                    if price is None:
                        price = getattr(p, "price", None) or getattr(p, "old_price", 0)

                    OrderItem.objects.create(
                        order=order,
                        product=p,
                        size=size_name,
                        quantity=qty,
                        price=price,
                    )

                    ProductSize.objects.filter(product=p, size__name=size_name).update(stock=F("stock") - qty)

                # 4) remove items from cart for this user (if using cart)
                CartItem.objects.filter(user=request.user, product_id__in=prod_ids).delete()

            return Response({"detail": "Payment verified and order created", "order_id": order.id}, status=status.HTTP_200_OK)

        except IntegrityError as e:
            traceback.print_exc()
            return Response({"error": "database_integrity_error", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            traceback.print_exc()
            return Response({"error": "product_not_found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": "verification_failed", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        # any top-level unexpected error
        traceback.print_exc()
        return Response({"error": "server_error", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
