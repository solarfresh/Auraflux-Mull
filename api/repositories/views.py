import logging

from adrf.views import APIView
from asgiref.sync import sync_to_async
from core.constants import ProcessStatus
from core.utils import get_serialized_data, instance_to_data
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from iam.permissions import HasRequiredScope
from messaging.constants import ProcessRepositoryFile
from messaging.tasks import publish_event
from repositories.models import RepositoryFile, SupportedFileType
from repositories.serializers import RepositoryFileSerializer
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from services.storage import FileStorageService

logger = logging.getLogger(__name__)


class RepositoryFileView(APIView):
    """
    API view for uploading document files into the repository and triggering
    background processing (parsing, chunking, and embedding).
    """

    parser_classes = [MultiPartParser, FormParser]
    MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

    permission_classes = [HasRequiredScope]

    def get_permissions(self):
        if self.request.method == 'GET':
            self.required_scope = 'mull:read'
        elif self.request.method == 'POST':
            self.required_scope = 'mull:write'

    async def get(self, request, *args, **kwargs):
        user = request.user

        query = {'user_id': user.id}
        data = await sync_to_async(get_serialized_data)(query, RepositoryFile, RepositoryFileSerializer, many=True)
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Upload a document file",
        description="Uploads a document (PDF, DOCX, TXT, CSV), registers a RepositoryFile entry, and triggers chunk processing.",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Single file to upload'
                    },
                    'files': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'binary'},
                        'description': 'Multiple files to upload'
                    }
                }
            }
        },
        responses={202: RepositoryFileSerializer, 400: OpenApiTypes.OBJECT}
    )
    async def post(self, request, project_id, *args, **kwargs):
        user = request.user
        uploaded_files = request.FILES.getlist('files') or request.FILES.getlist('file')

        if not uploaded_files:
            single_file = request.FILES.get('file')
            if single_file:
                uploaded_files = [single_file]

        if not uploaded_files:
            return Response(
                {"error": "No files or file was provided in the request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        storage_service = FileStorageService()
        successful_records = []
        failed_files = []

        valid_types = [choice[0] for choice in SupportedFileType.choices]
        for uploaded_file in uploaded_files:
            filename = uploaded_file.name

            is_valid, error_msg = self._validate_file(uploaded_file, valid_types)
            if not is_valid:
                failed_files.append({"file_name": filename, "reason": error_msg})
                continue

            try:
                file_record = await sync_to_async(self._save_single_file_record)(
                    uploaded_file=uploaded_file,
                    project_id=project_id,
                    user_id=str(user.id),
                    storage_service=storage_service
                )

                publish_event.delay(
                    event_type=ProcessRepositoryFile.name,
                    payload={
                        'file_id': str(file_record.id),
                    },
                    queue=ProcessRepositoryFile.queue
                )
                successful_records.append(file_record)
            except Exception as e:
                failed_files.append({"file_name": filename, "reason": f"Internal error during save: {str(e)}"})

        response_data = {
            "successCount": len(successful_records),
            "failedCount": len(failed_files),
            "successfulFiles": await sync_to_async(instance_to_data)(successful_records, RepositoryFileSerializer, many=True),
            "failedFiles": failed_files
        }

        response_status = status.HTTP_202_ACCEPTED if successful_records else status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=response_status)

    def _validate_file(self, uploaded_file, valid_types) -> tuple[bool, str | None]:
        filename = uploaded_file.name

        if uploaded_file.size > self.MAX_FILE_SIZE_BYTES:
            max_mb = self.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            return False, f"File size exceeds limit ({max_mb} MB)."

        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext not in valid_types:
            return False, f"Unsupported file type '.{ext}'."

        return True, None

    def _save_single_file_record(
        self,
        uploaded_file,
        user_id: str,
        project_id: str,
        storage_service: FileStorageService
    ) -> RepositoryFile:
        filename = uploaded_file.name
        ext = filename.split('.')[-1].lower()
        human_readable_size = self._format_file_size(uploaded_file.size)

        with transaction.atomic():
            file_record = RepositoryFile.objects.create(
                user_id=user_id,
                project_id=project_id,
                file_name=filename,
                file_size=human_readable_size,
                file_type=ext,
                status=ProcessStatus.QUEUED
            )

            file_path, storage_type = storage_service.save_file(
                uploaded_file=uploaded_file,
                folder_prefix=f'{project_id}/repository',
            )
            file_record.file_path = file_path
            file_record.storage_type = storage_type
            file_record.save(update_fields=['file_path', 'storage_type'])

        return file_record

    @staticmethod
    def _format_file_size(size_in_bytes: int) -> str:
        """Helper function to format bytes to human-readable file size."""
        size: float = float(size_in_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"

            size /= 1024.0

        return f"{size:.1f} TB"


class RepositoryFileDetailView(APIView):
    """
    API view for retrieving, updating, or deleting a specific repository file.
    """
    permission_classes = [HasRequiredScope]

    def get_permissions(self):
        if self.request.method == 'GET':
            self.required_scope = 'mull:read'
        elif self.request.method in ['PUT', 'PATCH', 'DELETE']:
            self.required_scope = 'mull:write'

    async def delete(self, request, project_id, file_id, *args, **kwargs):
        user = request.user

        result, error_msg = await sync_to_async(self._get_and_delete_file)(
            user_id=str(user.id),
            project_id=project_id,
            file_id=file_id
        )

        if error_msg:
            return Response(
                {"error": error_msg},
                status=status.HTTP_404_NOT_FOUND
            )

        file_path, storage_type = result if result else (None, None)

        if file_path:
            try:
                storage_service = FileStorageService()
                await sync_to_async(storage_service.delete_file)(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete physical file from storage: {str(e)}")

        return Response(
            {"message": "File deleted successfully.", "id": file_id},
            status=status.HTTP_200_OK
        )

    def _get_and_delete_file(self, user_id: str, project_id: str, file_id: str):
        try:
            file_record = RepositoryFile.objects.get(
                id=file_id,
                project_id=project_id,
                user_id=user_id
            )
        except RepositoryFile.DoesNotExist:
            return None, "File not found or permission denied."

        file_path = file_record.file_path
        storage_type = file_record.storage_type

        file_record.delete()

        return (file_path, storage_type), None
