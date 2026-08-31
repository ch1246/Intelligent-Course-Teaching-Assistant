from django.urls import path
from . import views

urlpatterns = [
    path('vector-db/collections', views.collection_list, name='vector-collections'),
    path('vector-db/collections/<int:pk>', views.collection_detail, name='vector-collection-detail'),
    path('vector-db/collections/<int:pk>/reindex', views.reindex, name='vector-collection-reindex'),
    path('vector-db/documents/upload', views.upload_document, name='vector-document-upload'),
]
