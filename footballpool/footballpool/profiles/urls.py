from django.contrib.auth.views import LogoutView
from django.urls import path

from footballpool.profiles import views

urlpatterns = [
    path('', views.TemporaryHomepageView.as_view(), name='homepage'),
    path('register/', views.RegisterUserView.as_view(), name='register_user'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/<str:username>/', views.ViewProfileView.as_view(), name='view_profile'),
    path('profile/<str:username>/edit/', views.EditProfileView.as_view(), name='edit_profile'),
]