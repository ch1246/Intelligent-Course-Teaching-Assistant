from django.urls import path
from . import views

urlpatterns = [
    path('my-sidebar', views.my_sidebar, name='my-sidebar'),
    path('home-stats', views.student_home_stats, name='student-home-stats'),
    path('<int:course_id>/dashboard', views.dashboard, name='course-dashboard'),
    path('<int:course_id>/chat-stats', views.chat_stats, name='course-chat-stats'),
    path('<int:course_id>/learning-time', views.learning_time, name='course-learning-time'),
    path('<int:course_id>/summary', views.course_summary, name='course-summary'),
]
