from django.urls import path
from . import views

urlpatterns = [
    path("users", views.user_list, name="admin-users"),
    path("users/<int:pk>", views.user_detail, name="admin-user-detail"),
    # Registration management
    path("registrations", views.registration_list, name="admin-registrations"),
    path("registrations/<int:pk>/approve", views.approve_registration, name="admin-registration-approve"),
    path("registrations/<int:pk>/reject", views.reject_registration, name="admin-registration-reject"),
    path("registrations/batch-approve", views.batch_approve, name="admin-registration-batch"),
    # Excel import
    path("registrations/import", views.import_excel, name="admin-registration-import"),
]