from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path("api/auth/", include("accounts.urls")),
    path("api/profile/", include("accounts.urls_profile")),
    path("api/messages/", include("accounts.urls_messages")),
    # Admin management
    path("api/admin/", include("accounts.urls_admin")),
    path("api/admin/", include("courses.urls_admin")),
    path("api/admin/", include("enrollments.urls_admin")),
    path("api/admin/", include("vector_db.urls")),
    path("api/admin/", include("settings_app.urls_admin")),
    path("api/admin/", include("dashboard.urls_admin")),
    path("api/admin/", include("prompt_engine.urls")),
    path("api/admin/", include("context_engine.urls")),
    path("api/admin/", include("harness.urls")),
    # Course
    path("api/course/", include("courses.urls")),
    path("api/course/", include("enrollments.urls")),
    path("api/course/", include("chat.urls")),
    path("api/course/", include("dashboard.urls")),
    # Files
    path("api/files/", include("files_app.urls")),
    # Settings
    path("api/settings/", include("settings_app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
