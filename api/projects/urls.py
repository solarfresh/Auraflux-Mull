from agents.views import AgentConfigDetailAPIView, AgentConfigListAPIView
from django.urls import path
from embeddings.views import (EmbeddingConfigDetailAPIView,
                              EmbeddingConfigListAPIView)
from projects.views import ProjectListCreateAPIView
from repositories.views import RepositoryFileDetailView, RepositoryFileView

urlpatterns = [
    path('', ProjectListCreateAPIView.as_view(), name='project-list-create'),
    path('<str:project_id>/agents/', AgentConfigListAPIView.as_view(), name='agent-configs'),
    path('<str:project_id>/agents/<str:agent_id>/', AgentConfigDetailAPIView.as_view(), name='agent-configs-detail'),
    path('<str:project_id>/embeddings/', EmbeddingConfigListAPIView.as_view(), name='embedding-configs'),
    path('<str:project_id>/embeddings/<str:embedding_id>/', EmbeddingConfigDetailAPIView.as_view(), name='embedding-configs-detail'),
    path('<str:project_id>/files/', RepositoryFileView.as_view(), name='repository-files'),
    path('<str:project_id>/files/<str:file_id>/', RepositoryFileDetailView.as_view(), name='repository-file-detail'),
]
