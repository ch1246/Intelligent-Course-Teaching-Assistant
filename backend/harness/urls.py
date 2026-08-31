from django.urls import path
from . import views

urlpatterns = [
    path("pipelines", views.pipeline_list, name="pipelines"),
    path("pipelines/<int:pk>", views.pipeline_detail, name="pipeline-detail"),
    path("pipelines/<int:pk>/default", views.pipeline_set_default, name="pipeline-default"),
    path("traces", views.trace_list, name="traces"),
    path("traces/<int:pk>", views.trace_detail, name="trace-detail"),
]
