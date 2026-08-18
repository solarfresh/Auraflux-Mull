from django.urls import path
from projects.views import ProjectListCreateAPIView
from repositories.views import RepositoryFileView, RepositoryFileDetailView


urlpatterns = [
    path('', ProjectListCreateAPIView.as_view(), name='project-list-create'),
    path('<str:project_id>/files/', RepositoryFileView.as_view(), name='repository-files'),
    path('<str:project_id>/files/<str:file_id>/', RepositoryFileDetailView.as_view(), name='repository-file-detail'),
]
