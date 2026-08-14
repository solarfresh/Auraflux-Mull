import logging

from adrf.views import APIView
from asgiref.sync import sync_to_async
from drf_spectacular.utils import (OpenApiParameter, OpenApiResponse,
                                   extend_schema)
from projects.models import Project
from projects.serializers import ProjectSerializer
from rest_framework import status
from rest_framework.response import Response
from core.utils import get_serialized_data, create_serialized_data
from iam.permissions import HasRequiredScope

logger = logging.getLogger(__name__)


class ProjectListCreateAPIView(APIView):
    """
    Handles the listing and creation of projects.
    """

    permission_classes = [HasRequiredScope]

    def get_permissions(self):
        if self.request.method == 'GET':
            self.required_scope = 'mull:read'
        elif self.request.method == 'POST':
            self.required_scope = 'mull:write'

    @extend_schema(
        summary="Retrieve project list",
        description="Returns a list of all projects in the system. Optionally filters projects by a specific tag.",
        parameters=[
            OpenApiParameter(
                name="tag",
                type=str,
                description="Filter projects by a specific tag",
                required=False
            )
        ],
        responses={200: ProjectSerializer(many=True)}
    )
    async def get(self, request, *args, **kwargs):
        user = request.user
        tag_filter = request.query_params.get('tag')

        query = {'user_id': user.id}
        if tag_filter:
            # Filter the JSONField array for the specific tag
            query['tags__contains'] = [tag_filter]

        data = await sync_to_async(get_serialized_data)(query, Project, ProjectSerializer, many=True)
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create a new project",
        description="Creates a new project using the provided data.",
        request=ProjectSerializer,
        responses={
            201: ProjectSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    )
    async def post(self, request, *args, **kwargs):
        user = request.user
        payload = request.data

        try:
            data = await sync_to_async(create_serialized_data)(payload, ProjectSerializer, user_id=str(user.id))
        except ValueError as errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(data, status=status.HTTP_201_CREATED)

