import logging

from adrf.views import APIView
from asgiref.sync import sync_to_async
from drf_spectacular.utils import (OpenApiParameter, OpenApiResponse,
                                   extend_schema)
from projects.models import Project
from projects.serializers import ProjectSerializer
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ProjectListCreateAPIView(APIView):
    """
    Handles the listing and creation of projects.
    """

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
        # 1. Get the tag query parameter
        tag_filter = request.query_params.get('tag')

        # 2. Query the database
        queryset = Project.objects.all()

        if tag_filter:
            # Filter the JSONField array for the specific tag
            queryset = queryset.filter(tags__contains=[tag_filter])

        # 3. Convert queryset to list and serialize asynchronously
        projects = await sync_to_async(list)(queryset)
        serializer = ProjectSerializer(projects, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

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
        serializer = ProjectSerializer(data=request.data)

        # Validate and save data
        if serializer.is_valid():
            # Save the serializer instance using sync_to_async since ModelSerializer.save() is synchronous
            await sync_to_async(serializer.save)()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
