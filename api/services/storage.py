import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Generator

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

    def delete_file(self, file_path: str) -> bool:
        """
        Deletes a physical file from the storage engine if it exists.

        Args:
            file_path (str): Relative file path or S3 key to be deleted.

        Returns:
            bool: True if the file was successfully deleted or didn't exist,
                  False if an error occurred during deletion.
        """
        if not file_path:
            return False

        try:
            # Check file existence prior to deletion to prevent unnecessary storage errors
            if self.storage.exists(file_path):
                self.storage.delete(file_path)
            return True
        except Exception as e:
            # Log the error if necessary in your application context
            return False

    def read_file_bytes(self, file_path: str) -> bytes:
        """
        Reads and returns the complete binary content of a file from storage.
        Encapsulates underlying storage access (Local, S3, etc.).

        Args:
            file_path (str): Relative file path or S3 key.

        Returns:
            bytes: Raw binary content of the file.

        Raises:
            FileNotFoundError: If file path is invalid or file doesn't exist.
        """
        if not file_path or not self.storage.exists(file_path):
            raise FileNotFoundError(f"File not found in storage: {file_path}")

        with self.storage.open(file_path, mode="rb") as f:
            return f.read()

    @contextmanager
    def get_file_stream(self, file_path: str) -> Generator[IO[bytes], None, None]:
        """
        Context manager that yields a file-like stream object.
        Ensures underlying storage handles/sockets are cleanly closed.

        Args:
            file_path (str): Relative file path or S3 key.

        Yields:
            io.BufferedIOBase: Binary file-like stream object.
        """
        if not file_path or not self.storage.exists(file_path):
            raise FileNotFoundError(f"File not found in storage: {file_path}")

        f = self.storage.open(file_path, mode="rb")
        try:
            yield f
        finally:
            f.close()
