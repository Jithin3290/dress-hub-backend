# user/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import login
from .serializers import SignupSerializer
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import logging, traceback
from .models import SignupOTP, User
from .serializers import SignupSerializer, LoginSerializer, UserSerializer, ProfileSerializer
from django.utils import timezone
import random
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

class SendSignupOTPAPIView(APIView):
    authentication_classes = [] 
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"email": ["Email is required"]}, status=status.HTTP_400_BAD_REQUEST)

        # simple rate limit: max 3 OTPs per minute per email
        one_min_ago = timezone.now() - timezone.timedelta(minutes=1)
        recent = SignupOTP.objects.filter(email=email, created_at__gte=one_min_ago).count()
        if recent >= 3:
            return Response({"detail": "Too many OTP requests, try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = f"{random.randint(100000, 999999)}"
        otp = SignupOTP.objects.create(email=email, code=code)

        subject = "Your signup verification code"
        message = f"Your signup verification code is {code}. It will expire in 5 minutes."
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@localhost"

        try:
            sent = send_mail(subject, message, from_email, [email], fail_silently=False)
            if sent < 1:
                logger.error("send_mail returned 0 while sending OTP to %s", email)
                # cleanup
                otp.delete()
                return Response({"detail": "Failed to send email (0 delivered)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            # log full traceback to server logs for immediate debugging
            logger.exception("Error sending signup OTP to %s: %s", email, exc)
            # delete OTP to avoid leaking valid codes when mail fails
            try:
                otp.delete()
            except Exception:
                logger.exception("Failed to delete OTP after mail error for %s", email)
            # return a short error to client, include exception string for dev (trimmed)
            return Response({"detail": f"Failed to send email: {str(exc)[:300]}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"detail": "OTP sent"}, status=status.HTTP_200_OK)



class OTPHelper:
    @staticmethod
    def validate_otp(email, code):
        if not email or not code:
            return None, "OTP and email required"

        otp = SignupOTP.objects.filter(email=email, code=code, used=False).order_by("-created_at").first()
        if not otp:
            return None, "Invalid code"
        if otp.is_expired():
            return None, "Expired code"
        return otp, None

class SignupView(APIView):
    authentication_classes = [] 
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        # Expect an 'otp' field in request.data (comes from frontend)
        otp_code = request.data.get("otp")
        email = request.data.get("email")
        # at start of SignupView.post
 

        # If you require OTP for signup, validate here
        if not otp_code:
            return Response({"otp": ["OTP is required"]}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj, otp_err = OTPHelper.validate_otp(email, otp_code)
        if otp_err:
            return Response({"otp": [otp_err]}, status=status.HTTP_400_BAD_REQUEST)

        # Proceed with existing serializer validation / creation
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # mark OTP used
        try:
            otp_obj.mark_used()
        except Exception:
            # not critical; continue
            pass

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
    authentication_classes = [] 
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, email=email, password=password)
        #login(request, user)
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
        response.delete_cookie("sessionid")
        response.delete_cookie("csrftoken")

        
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
        

@api_view(["POST"])
@permission_classes([AllowAny])
def contact_message(request):
    name = request.data.get("name")
    email = request.data.get("email")
    message = request.data.get("message")

    if not all([name, email, message]):
        return Response({"error": "Missing fields"}, status=400)

    subject = f"Contact form message from {name}"
    body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        ["jithin3290@gmail.com"],     
        fail_silently=False,
    )

    return Response({"detail": "Message sent"}, status=200)