from django.urls import path
from . import views

urlpatterns = [
    path("prompts", views.template_list, name="prompt-templates"),
    path("prompts/<int:pk>", views.template_detail, name="prompt-template-detail"),
    path("prompts/<int:pk>/preview", views.template_preview, name="prompt-template-preview"),
    path("prompts/<int:pk>/versions", views.template_versions, name="prompt-template-versions"),
    path("prompts/<int:pk>/rollback", views.template_rollback, name="prompt-template-rollback"),
    path("prompts/<int:pk>/default", views.template_set_default, name="prompt-template-default"),
]
