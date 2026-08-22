import logging

from core.celery_app import celery_app
from core.constants import ProcessStatus
from messaging.constants import ProcessRepositoryChunk, ProcessRepositoryFile
from messaging.tasks import publish_event
from repositories.models import RepositoryFile
from repositories.utils import get_chunker, get_parser_by_file_type
from services.storage import FileStorageService

logger = logging.getLogger(__name__)


@celery_app.task(name=ProcessRepositoryChunk.name, ignore_result=True)
def process_repository_chunk_task(event_type: str, payload: dict):
    task_id = process_repository_chunk_task.request.id
    file_record_id = payload.get('file_record_id')
    chunk_payload = payload.get('chunk_payload')

    # TODO: 3. Perform text chunking and call the embedding model
    # TODO: 4. Write to vector database (OpenSearch / Pinecone)


@celery_app.task(name=ProcessRepositoryFile.name, ignore_result=True)
def process_repository_file_task(event_type: str, payload: dict):
    """
    Background Celery task to parse, chunk, and embed a repository file.
    """
    task_id = process_repository_file_task.request.id
    file_record_id = payload.get('file_record_id')
    logger.info(f"Received task {task_id} to process file with ID: {file_record_id}")

    try:
        file_record = RepositoryFile.objects.get(id=file_record_id)

        file_record.status = ProcessStatus.PROCESSING
        file_record.save(update_fields=['status'])

        logger.info(f"Starting background processing for file: {file_record.file_name} (ID: {file_record_id})")

        storage_service = FileStorageService()
        if file_record.file_path is None:
            raise ValueError(f"RepositoryFile {file_record_id} has no file path")

        file_bytes = storage_service.read_file_bytes(file_record.file_path)
        parser = get_parser_by_file_type(file_record.file_type)
        sections = parser.safe_parse(
            file_input=file_bytes,
            filename=file_record.file_name
        )

        logger.info(f"Successfully parsed {len(sections)} sections from {file_record.file_name}")

        chunker = get_chunker()
        chunks = chunker.chunk_sections(sections)

        logger.info(f"Generated {len(chunks)} chunks for file: {file_record.file_name}")

        for chunk in chunks:
            publish_event.delay(
                event_type=ProcessRepositoryChunk.name,
                payload={
                    'file_record_id': file_record_id,
                    'chunk_payload': chunk.model_dump_json()
                },
                queue=ProcessRepositoryChunk.queue
            )

        logger.info(f"File {file_record_id} split into {len(chunks)} chunks and dispatched successfully.")

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
