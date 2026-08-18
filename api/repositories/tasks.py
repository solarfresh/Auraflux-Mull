import logging

from core.celery_app import celery_app
from core.constants import ProcessStatus
from messaging.constants import ProcessRepositoryFile
from repositories.models import RepositoryFile

logger = logging.getLogger(__name__)


@celery_app.task(name=ProcessRepositoryFile.name, ignore_result=True)
def process_repository_file_task(file_record_id: str):
    """
    Background Celery task to parse, chunk, and embed a repository file.
    """
    task_id = process_repository_file_task.request.id
    logger.info(f"Received task {task_id} to process file with ID: {file_record_id}")

    try:
        file_record = RepositoryFile.objects.get(id=file_record_id)

        file_record.status = ProcessStatus.PROCESSING
        file_record.save(update_fields=['status'])

        logger.info(f"Starting background processing for file: {file_record.file_name} (ID: {file_record_id})")

        # TODO: 1. Read physical file from storage (default_storage.open(file_record.file_path))
        # TODO: 2. Parse document text (PDF/Word/TXT)
        # TODO: 3. Perform text chunking and call the embedding model
        # TODO: 4. Write to vector database (OpenSearch / Pinecone)

        file_record.status = ProcessStatus.SUCCESS
        file_record.save(update_fields=['status'])
        logger.info(f"Successfully processed file: {file_record_id}")

    except RepositoryFile.DoesNotExist:
        logger.error(f"RepositoryFile with ID {file_record_id} not found.")
    except Exception as exc:
        logger.error(f"Error processing file {file_record_id}: {exc}")
        try:
            file_record = RepositoryFile.objects.get(id=file_record_id)
            file_record.status = ProcessStatus.ERROR
            file_record.save(update_fields=['status'])
        except Exception:
            pass

        raise process_repository_file_task.retry(exc=exc, countdown=60)
