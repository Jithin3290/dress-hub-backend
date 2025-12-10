from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers
from django.db.models import Q

from order.models import Order
from .serializers import AdminOrderSerializer


class AdminOrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class AdminOrderList(APIView):
    permission_classes = [IsAdminUser]

    ALLOWED_ORDERING = {
        "created_at", "-created_at",
        "order_status", "-order_status",
        "total_amount", "-total_amount",
    }

    def get(self, request):
        """
        GET /api/v1/admin/admin_orders/?page=1&page_size=10&search=foo&ordering=-created_at
        """
        try:
            qs = Order.objects.select_related("user").prefetch_related("items__product").all()

            search = request.query_params.get("search")
            if search:
                # search by user email or name; id only when numeric
                q = Q(user__email__icontains=search) | Q(user__name__icontains=search)
                if search.isdigit():
                    q |= Q(id=int(search))
                qs = qs.filter(q)

            ordering = request.query_params.get("ordering")
            if ordering and ordering in self.ALLOWED_ORDERING:
                qs = qs.order_by(ordering)

            paginator = AdminOrderPagination()
            page = paginator.paginate_queryset(qs, request)
            serializer = AdminOrderSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)

        except Exception:
            return Response(
                {"detail": "Invalid request or internal error while processing query."},
                status=status.HTTP_400_BAD_REQUEST,
            )

class AdminOrderDetail(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, pk):
        try:
            return Order.objects.select_related("user").prefetch_related("items__product").get(pk=pk)
        except Order.DoesNotExist:
            return None

    def get(self, request, pk):
        order = self.get_object(pk)
        if not order:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminOrderSerializer(order, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk):
        """
        Partial update order fields (admin).
        Example body: { "shipping_address": "...", "phone": "..." }
        """
        order = self.get_object(pk)
        if not order:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminOrderSerializer(order, data=request.data, partial=True, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminOrderStatus(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, pk):
        try:
            return Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return None

    def patch(self, request, pk):
        """
        Patch only order_status.
        Body: { "status": "SHIPPED" }
        """
        order = self.get_object(pk)
        if not order:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = {choice[0] for choice in Order.ORDER_STATUS_CHOICES}
        if new_status not in valid_statuses:
            return Response({"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        order.order_status = new_status
        order.save(update_fields=["order_status", "updated_at"])
        serializer = AdminOrderSerializer(order, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
