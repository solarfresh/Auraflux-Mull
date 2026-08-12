from django.urls import path
from projects.views import ProjectListCreateAPIView


urlpatterns = [
    path('', ProjectListCreateAPIView.as_view(), name='project-list-create'),
]
