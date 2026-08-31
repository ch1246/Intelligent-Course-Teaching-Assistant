from django.urls import path
from . import views

urlpatterns = [
    path('', views.file_list, name='file-list'),
    path('<int:pk>', views.file_detail, name='file-detail'),
]
