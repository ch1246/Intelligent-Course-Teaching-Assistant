from django.urls import path
from . import views

urlpatterns = [
    path("context-strategies", views.strategy_list, name="context-strategies"),
    path("context-strategies/<int:pk>", views.strategy_detail, name="context-strategy-detail"),
    path("context-strategies/<int:pk>/default", views.strategy_set_default, name="context-strategy-default"),
]
