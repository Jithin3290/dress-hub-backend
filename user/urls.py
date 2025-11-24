from django.urls import path
from .views import SignupView,LoginView,LogoutView,ProfileView

urlpatterns = [
    path("signup/", SignupView.as_view()), 
    path("login/", LoginView.as_view()),        
    path("logout/", LogoutView.as_view()),   
    path("profile/", ProfileView.as_view()),                   
                
           
                   
]
