from django.urls import path
from .views import SignupView,LoginView,LogoutView,ProfileView,SendSignupOTPAPIView, contact_message

urlpatterns = [
    path("send-signup-otp/", SendSignupOTPAPIView.as_view()),
    path("signup/", SignupView.as_view()), 
    path("login/", LoginView.as_view()),        
    path("logout/", LogoutView.as_view()),   
    path("profile/", ProfileView.as_view()),                   
    path("contact/", contact_message),
          
           
                   
]
