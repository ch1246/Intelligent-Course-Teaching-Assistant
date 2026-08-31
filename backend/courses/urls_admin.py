from django.urls import path
from . import views

urlpatterns = [
    path('courses/teachers', views.teacher_list, name='admin-course-teachers'),
    path('courses', views.admin_course_list, name='admin-courses'),
    path('courses/<int:pk>', views.admin_course_detail, name='admin-course-detail'),
]