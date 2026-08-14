import uuid
from pathlib import Path
from django.conf import settings
from django.core.files.storage import Storage, default_storage
from django.core.files.uploadedfile import UploadedFile


class FileStorageService:
    """
    Handles physical file persistence layer. Supports standard Django default
    storage as well as custom Storage instances (e.g., S3, Azure Blob, or custom buckets).
    """

    def __init__(self, storage_instance: Storage | None = None) -> None:
        """
        Initialize storage service with a specific storage instance or fall back
        to Django's default storage engine.
        """
        self.storage: Storage = storage_instance or default_storage

    def save_file(
        self,
        uploaded_file: UploadedFile,
        folder_prefix: str = "uploads"
    ) -> tuple[str, str]:
        """
        Persists an uploaded file using the underlying storage engine.

        Args:
            uploaded_file (UploadedFile): The incoming file payload from the request.
            folder_prefix (str): Directory or prefix path within the storage bucket.

        Returns:
            tuple[str, str]:
                - file_path: Relative file path or S3 key where the file was saved.
                - storage_type: Identifier of the storage backend (e.g., 's3', 'local').
        """
        # 1. Generate a collision-resistant unique file path
        file_ext = Path(uploaded_file.name).suffix if uploaded_file.name else ""
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"

        clean_prefix = folder_prefix.strip("/")
        save_path = f"{clean_prefix}/{unique_filename}" if clean_prefix else unique_filename

        # 2. Persist file to storage engine
        saved_relative_path = self.storage.save(save_path, uploaded_file)

        # 3. Determine the storage provider backend type
        storage_backend_name = getattr(
            settings, "STORAGES", {}
        ).get("default", {}).get("BACKEND", "local")

        if "s3" in storage_backend_name.lower() or "boto3" in storage_backend_name.lower():
            storage_type = "s3"
        else:
            storage_type = "local"

        return saved_relative_path, storage_type
