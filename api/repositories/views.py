from core.constants import ProcessStatus
from django.core.files.storage import Storage
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from repositories.models import RepositoryFile, SupportedFileType
from repositories.serializers import RepositoryFileSerializer
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from services.storage import FileStorageService


class RepositoryFileUploadView(APIView):
    """
    API view for uploading document files into the repository and triggering
    background processing (parsing, chunking, and embedding).
    """
    parser_classes = [MultiPartParser, FormParser]
    MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

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
                        'description': 'File to be uploaded'
                    }
                },
                'required': ['file']
            }
        },
        responses={202: RepositoryFileSerializer, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request, project_id, *args, **kwargs):
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response(
                {"error": "No file was provided in the request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if uploaded_file.size > self.MAX_FILE_SIZE_BYTES:
            return Response(
                {"error": f"File size exceeds the maximum limit of {self.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."},
                status=status.HTTP_400_BAD_REQUEST
            )

        filename = uploaded_file.name
        ext = filename.split('.')[-1].lower() if '.' in filename else ''

        valid_types = [choice[0] for choice in SupportedFileType.choices]
        if ext not in valid_types:
            return Response(
                {"error": f"Unsupported file type '.{ext}'. Supported types: {valid_types}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        human_readable_size = self._format_file_size(uploaded_file.size)
        with transaction.atomic():
            file_record = RepositoryFile.objects.create(
                file_name=filename,
                file_size=human_readable_size,
                file_type=ext,
                status=ProcessStatus.QUEUED
            )

            file_path, storage_type = self._save_to_storage(
                uploaded_file=uploaded_file,
                folder_prefix=f'{project_id}/repository'
            )
            file_record.file_path = file_path
            file_record.storage_type = storage_type
            file_record.save(update_fields=['file_path', 'storage_type'])

            # process_file_chunks_task.delay(str(file_record.id))

        serializer = RepositoryFileSerializer(file_record)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    def _save_to_storage(
        self,
        uploaded_file,
        folder_prefix='uploads',
        custom_storage: Storage | None = None
    ) -> tuple[str, str]:
        """
        Delegates file persistence to FileStorageService.
        Allows custom storage engines to be injected on demand.
        """
        storage_service = FileStorageService(storage_instance=custom_storage)
        return storage_service.save_file(uploaded_file, folder_prefix)

    @staticmethod
    def _format_file_size(size_in_bytes: int) -> str:
        """Helper function to format bytes to human-readable file size."""
        size: float = float(size_in_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"

            size /= 1024.0

        return f"{size:.1f} TB"
