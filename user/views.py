# user/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .serializers import SignupSerializer
from .models import User
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, UserSerializer,ProfileSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import logging, traceback

class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "message": "Signup successful",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "phone_number": user.phone_number,
                    "profile_picture": str(user.profile_picture) if user.profile_picture else None,
                    "is_banned": user.is_banned,
                    
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, email=email, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response(
            {
                "message": "Login successful",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

        # Set cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,     # set True in production (HTTPS)
            samesite="Lax",
            max_age=60 * 60,  # 1 hour
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,     # set True in production (HTTPS)
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )

        return response

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        response = Response(
            {"message": "Logged out"},
            status=status.HTTP_200_OK
        )

        # delete both JWT cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
    
logger = logging.getLogger(__name__)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        serializer = ProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        # debug line: helps confirm if authentication succeeded
        logger.debug("ProfileView.patch request.user: id=%s authenticated=%s", getattr(request.user, "id", None), request.user.is_authenticated)

        try:
            serializer = ProfileSerializer(request.user, data=request.data, partial=True, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Profile update error: %s\n%s", exc, tb)
            # Helpful during development. Remove the traceback in production.
            return Response({"detail": str(exc), "traceback": tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)