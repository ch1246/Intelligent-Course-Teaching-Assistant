from django.urls import path
from . import views

urlpatterns = [
    path('my-courses', views.my_courses, name='my-courses'),
    path('catalog', views.course_catalog, name='course-catalog'),
    path('<int:pk>', views.course_detail, name='course-detail'),
]
