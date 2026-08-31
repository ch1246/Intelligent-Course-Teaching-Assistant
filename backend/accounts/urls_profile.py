from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('avatar', views.avatar_upload, name='avatar-upload'),
]