from django.urls import path
from accounts.views import get_menu_list

urlpatterns = [
    path('getMenuList', get_menu_list, name='menu-list'),
]
