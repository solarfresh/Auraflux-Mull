import logging

from adrf.views import APIView
from agents.models import AgentConfig
from agents.serializers import AgentConfigSerializer
from asgiref.sync import sync_to_async
from core.utils import get_serialized_data
from drf_spectacular.utils import OpenApiParameter, extend_schema
from iam.permissions import HasRequiredScope
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class AgentConfigListAPIView(APIView):
    """
    Handles the listing of agent configurations for a specific project.
    """

    permission_classes = [HasRequiredScope]

    def get_permissions(self):
        if self.request.method == 'GET':
            self.required_scope = 'mull:read'
        return super().get_permissions()

    @extend_schema(
        summary="Retrieve agent configuration list",
        description="Returns a list of all agent configurations belonging to a specific project.",
        parameters=[
            OpenApiParameter(
                name="project_id",
                type=str,
                description="The UUID of the project to filter agents by.",
                required=True,
                location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name="role",
                type=str,
                description="Optional: Filter by a specific agent role (e.g., 'Triples Extractor').",
                required=False,
                location=OpenApiParameter.QUERY
            )
        ],
        responses={
            200: AgentConfigSerializer(many=True),
            400: {"description": "Bad Request - project_id is required"}
        }
    )
    async def get(self, request, project_id, *args, **kwargs):
        user = request.user

        # Base query ensures project scope
        query = {
            'project_id': project_id
        }

        # Await the sync database operation
        data = await sync_to_async(get_serialized_data)(
            query,
            AgentConfig,
            AgentConfigSerializer,
            many=True
        )

        return Response(data, status=status.HTTP_200_OK)
