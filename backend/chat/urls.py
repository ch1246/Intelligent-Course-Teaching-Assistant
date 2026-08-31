from django.urls import path
from . import views

urlpatterns = [
    path("<int:course_id>/chat/sessions", views.sessions, name="chat-sessions"),
    path("<int:course_id>/chat/sessions/<int:session_id>", views.session_detail, name="chat-session-detail"),
    path("<int:course_id>/chat/sessions/<int:session_id>/messages", views.session_messages, name="chat-session-messages"),
    path("<int:course_id>/chat/completions", views.chat_completions, name="chat-completions"),
    # 用户记忆
    path("<int:course_id>/chat/memory", views.user_memory, name="chat-memory"),
    path("<int:course_id>/chat/memory/<int:memory_id>", views.delete_memory, name="chat-memory-delete"),
    path("<int:course_id>/chat/memory/bulk-update", views.memory_bulk_update, name="chat-memory-bulk"),
]
