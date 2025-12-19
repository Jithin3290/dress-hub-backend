from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination

from user.models import User
from .serializers import AdminUserSerializer

# reuse same pagination as before or tweak
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100



class UserListAPIView(APIView):
    """
    GET: list users with pagination, search and ordering.
    Query params:
      - page, page_size
      - search (searches name, email, phone_number)
      - ordering (e.g. 'name' or '-id')
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, format=None):
        qs = User.objects.all()

        # search
        search_q = request.query_params.get("search")
        if search_q:
            qs = qs.filter(
                Q(name__icontains=search_q)
                | Q(email__icontains=search_q)
                | Q(phone_number__icontains=search_q)
            )

        # ordering
        ordering = request.query_params.get("ordering")
        if ordering:
            # basic validation: allow hyphen + field or field
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-id")

        # paginate
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminUserSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class UserDetailAPIView(APIView):
    """
    GET: retrieve single user
    PATCH: partial update (use to toggle is_banned or update fields)
    DELETE: remove user
    """
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk, format=None):
        user = self.get_object(pk)
        serializer = AdminUserSerializer(user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk, format=None):
        user = self.get_object(pk)
        serializer = AdminUserSerializer(user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, format=None):
        user = self.get_object(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ToggleBanAPIView(APIView):
    """
    POST /user/{pk}/toggle-ban/
    Toggles is_banned and returns the updated user.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk, format=None):
        user = get_object_or_404(User, pk=pk)
        user.is_banned = not bool(user.is_banned)
        user.save()
        serializer = AdminUserSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
