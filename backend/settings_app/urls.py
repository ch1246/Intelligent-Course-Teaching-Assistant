from django.urls import path
from . import views

urlpatterns = [
    path('', views.system_settings, name='settings'),
]
