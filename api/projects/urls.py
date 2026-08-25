from agents.views import AgentConfigDetailAPIView, AgentConfigListAPIView
from django.urls import path
from projects.views import ProjectListCreateAPIView
from repositories.views import RepositoryFileDetailView, RepositoryFileView

urlpatterns = [
    path('', ProjectListCreateAPIView.as_view(), name='project-list-create'),
    path('<str:project_id>/agents/', AgentConfigListAPIView.as_view(), name='agent-configs'),
    path('<str:project_id>/agents/<str:agent_id>/', AgentConfigDetailAPIView.as_view(), name='agent-configs-detail'),
    path('<str:project_id>/files/', RepositoryFileView.as_view(), name='repository-files'),
    path('<str:project_id>/files/<str:file_id>/', RepositoryFileDetailView.as_view(), name='repository-file-detail'),
]
