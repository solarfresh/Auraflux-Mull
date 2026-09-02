import logging

from adrf.views import APIView
from asgiref.sync import sync_to_async
from core.utils import get_serialized_data, update_serialized_data_by_query
from drf_spectacular.utils import OpenApiParameter, extend_schema
from embeddings.models import EmbeddingConfig
from embeddings.serializers import EmbeddingConfigSerializer
from iam.permissions import HasRequiredScope
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class EmbeddingConfigListAPIView(APIView):
    """
    Handles the listing of embedding configurations for a specific project.
    """

    permission_classes = [HasRequiredScope]

    def get_permissions(self):
        if self.request.method == 'GET':
            self.required_scope = 'mull:read'
        return super().get_permissions()

    @extend_schema(
        summary="Retrieve embedding configuration list",
        description="Returns a list of all embedding configurations belonging to a specific project.",
        parameters=[
            OpenApiParameter(
                name="role",
                type=str,
                description="Optional: Filter by a specific embedding role (e.g., 'default_search').",
                required=False,
                location=OpenApiParameter.QUERY
            )
        ],
        responses={
            200: EmbeddingConfigSerializer(many=True),
            400: {"description": "Bad Request - project_id is required"}
        }
    )
    async def get(self, request, project_id, *args, **kwargs):
        # Base query ensures project scope
        query = {
            'project_id': project_id
        }

        # Optional filter by role
        role = request.query_params.get('role')
        if role:
            query['role'] = role

        # Await the sync database operation
        data = await sync_to_async(get_serialized_data)(
            query,
            EmbeddingConfig,
            EmbeddingConfigSerializer,
            many=True
        )

        return Response(data, status=status.HTTP_200_OK)


class EmbeddingConfigDetailAPIView(APIView):
    """
    Handles updating a specific embedding configuration.
    """

    permission_classes = [HasRequiredScope]

    def get_permissions(self):
        if self.request.method == 'PUT':
            self.required_scope = 'mull:write'
        return super().get_permissions()

    @extend_schema(
        summary="Update embedding configuration",
        description="Partially update an existing embedding configuration.",
        responses={
            200: EmbeddingConfigSerializer,
            400: {"description": "Bad Request - Invalid data"},
            404: {"description": "Not Found - Embedding configuration does not exist"}
        }
    )
    async def put(self, request, project_id, embedding_id, *args, **kwargs):
        request_data = request.data

        try:
            data = await sync_to_async(update_serialized_data_by_query)(
                {'id': embedding_id, 'project_id': project_id},
                request_data,
                EmbeddingConfig,
                EmbeddingConfigSerializer
            )
            return Response(data, status=status.HTTP_200_OK)
        except EmbeddingConfig.DoesNotExist:
            return Response(
                {"detail": "EmbeddingConfig not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
