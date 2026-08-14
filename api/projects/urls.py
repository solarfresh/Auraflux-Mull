from django.urls import path
from projects.views import ProjectListCreateAPIView
from repositories.views import RepositoryFileUploadView


urlpatterns = [
    path('', ProjectListCreateAPIView.as_view(), name='project-list-create'),
    path('<str:project_id>/files/upload/', RepositoryFileUploadView.as_view(), name='repository-file-upload'),
]
