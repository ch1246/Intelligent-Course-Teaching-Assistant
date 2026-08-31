from django.urls import path
from . import views

urlpatterns = [
    path('enroll-review', views.admin_enroll_list, name='admin-enroll-list'),
    path('enroll-review/<int:pk>', views.admin_enroll_review, name='admin-enroll-review'),
]
