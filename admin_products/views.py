# admin_products/views.py
import json
from collections.abc import Mapping
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q

from product.models import Product, Category, Size
from .serializers import AdminProductSerializer, CategorySerializer, SizeSerializer


class AdminProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 200


def _extract_sizes_as_strings(data):
    """
    Normalize incoming sizes_input into a list[str] or return None if absent.
    Handles JSON string, repeated fields, indexed fields, mapping/dict shapes,
    comma/space separated, single token string.
    """
    raw = data.get("sizes_input", None)

    if raw is None:
        return None

    # raw is list
    if isinstance(raw, list):
        out = []
        for el in raw:
            if el is None:
                continue
            if isinstance(el, (list, tuple)):
                for inner in el:
                    if inner is not None:
                        out.append(str(inner).strip())
            else:
                out.append(str(el).strip())
        return [s for s in out if s]

    # mapping/dict-like (e.g. {'0': ['S'], '1': ['M']})
    if isinstance(raw, Mapping):
        out = []
        try:
            items = sorted(raw.items(), key=lambda kv: int(str(kv[0]).strip()) if str(kv[0]).strip().isdigit() else kv[0])
        except Exception:
            items = raw.items()
        for k, v in items:
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                for inner in v:
                    if inner is not None and str(inner).strip():
                        out.append(str(inner).strip())
            else:
                if str(v).strip():
                    out.append(str(v).strip())
        return [s for s in out if s]

    # raw is string
    if isinstance(raw, str):
        s = raw.strip()
        # try JSON
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if x is not None and str(x).strip()]
        except Exception:
            pass
        # comma separated
        if "," in s:
            return [part.strip() for part in s.split(",") if part.strip()]
        # space separated
        if " " in s:
            return [part.strip() for part in s.split() if part.strip()]
        # single token
        if s:
            return [s]

    # fallback: QueryDict.getlist
    if hasattr(data, "getlist"):
        try:
            lst = data.getlist("sizes_input")
            if lst:
                out = []
                for el in lst:
                    if el is None:
                        continue
                    if isinstance(el, (list, tuple)):
                        for inner in el:
                            if inner is not None and str(inner).strip():
                                out.append(str(inner).strip())
                    else:
                        if str(el).strip():
                            out.append(str(el).strip())
                return out
        except Exception:
            pass

    return None


# admin_products/views.py (corrected)
class AdminProductListCreate(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        qs = Product.objects.select_related("category").prefetch_related("sizes__size")
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(category__name__icontains=search))
        category = request.query_params.get("category")
        if category:
            if str(category).isdigit():
                qs = qs.filter(category_id=int(category))
            else:
                qs = qs.filter(category__slug=category)
        ordering = request.query_params.get("ordering", "-created_at")
        allowed = {"created_at", "-created_at", "new_price", "-new_price", "name", "-name"}
        if ordering not in allowed:
            ordering = "-created_at"
        qs = qs.order_by(ordering)

        paginator = AdminProductPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminProductSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Build a plain dict from request.data (QueryDict/Mapping → plain scalars/lists)
        raw = request.data
        payload = {}

        # convert QueryDict-like to plain dict
        if hasattr(raw, "keys"):
            for k in raw.keys():
                try:
                    # getlist returns all values for repeated keys
                    vals = raw.getlist(k)
                except Exception:
                    vals = raw.get(k)
                    # wrap single scalar into list for uniformity
                    vals = [vals] if vals is not None else []
                # collapse single-value lists into scalar, but keep lists for repeated fields
                if isinstance(vals, (list, tuple)) and len(vals) == 1:
                    payload[k] = vals[0]
                else:
                    payload[k] = vals
        else:
            # fallback for non-QueryDict
            payload = dict(raw)

        # Normalize sizes_input into list[str]
        sizes_list = _extract_sizes_as_strings(payload if isinstance(payload, dict) else request.data)
        if sizes_list is not None:
            payload["sizes_input"] = sizes_list

        # If an actual uploaded file exists in request.FILES, ensure it's included in payload
        # (Files are not in request.data)
        if request.FILES and "image" in request.FILES:
            payload["image"] = request.FILES.get("image")

        # Debug prints (temporary)
       

        serializer = AdminProductSerializer(data=payload, context={"request": request})
        if serializer.is_valid():
            p = serializer.save()
            return Response(AdminProductSerializer(p, context={"request": request}).data, status=status.HTTP_201_CREATED)

        # debug output for failing validation
        try:
            print(">>> serializer.errors:", serializer.errors)
        except Exception:
            pass
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminProductDetail(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        try:
            return Product.objects.prefetch_related("sizes__size").get(pk=pk)
        except Product.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminProductSerializer(obj, context={"request": request}).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        data = request.data.copy()
        sizes_list = _extract_sizes_as_strings(data)
        if sizes_list is not None:
            data["sizes_input"] = sizes_list
        serializer = AdminProductSerializer(obj, data=data, partial=True, context={"request": request})
        if serializer.is_valid():
            p = serializer.save()
            return Response(AdminProductSerializer(p, context={"request": request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCategoryList(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Category.objects.all().order_by("name")
        return Response(CategorySerializer(qs, many=True).data)


class AdminSizeList(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Size.objects.all().order_by("name")
        return Response(SizeSerializer(qs, many=True).data)
