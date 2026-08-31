from django.urls import path
from . import views

urlpatterns = [
    path('login', views.login, name='auth-login'),
    path('register', views.register, name='auth-register'),
    path('getUserInfo', views.get_user_info, name='auth-userinfo'),
    path('refresh', views.refresh_token, name='auth-refresh'),
    path('change-password', views.change_password, name='auth-change-password'),
    path('forgot-password', views.forgot_password, name='auth-forgot-password'),
]
