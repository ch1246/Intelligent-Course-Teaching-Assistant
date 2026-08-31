from django.urls import path
from . import views

urlpatterns = [
    path('agent-api-configs', views.agent_api_config_list, name='agent-api-configs'),
    path('agent-api-configs/<int:pk>', views.agent_api_config_detail, name='agent-api-config-detail'),
    path('agent-api-configs/<int:pk>/default', views.set_default_config, name='agent-api-config-default'),
]
