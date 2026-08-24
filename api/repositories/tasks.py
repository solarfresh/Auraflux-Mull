import json
import logging
from typing import Dict, cast

from agents.models import AgentConfig
from agents.serializers import AgentConfigSerializer
from auraflux_core.rag.filters.base import FilterPipeline
from auraflux_core.rag.filters.semantic_filter import (
    GroundedInEvidenceFilter, SemanticQualityFilter)
from auraflux_core.rag.filters.static_filter import StaticRuleFilter
from auraflux_core.rag.schemas.chunker import (ChunkAlignment, ChunkConcept,
                                               ChunkKeywords, StandardChunk)
from core.celery_app import celery_app
from core.constants import ProcessStatus
from core.utils import create_serialized_data, get_serialized_data
from messaging.constants import (AgentRequest, ProcessConceptSynthesis,
                                 ProcessRepositoryChunk, ProcessRepositoryFile,
                                 ProcessTriplesExtractor)
from messaging.tasks import publish_event
from repositories.models import RepositoryFile
from repositories.serializers import ChunkDataSerializer
from repositories.utils import (get_chunker, get_parser_by_file_type,
                                mark_file_status)
from services.semaphore import get_raw_redis_client
from services.storage import FileStorageService

logger = logging.getLogger(__name__)


@celery_app.task(name=ProcessConceptSynthesis.name, ignore_result=True)
def process_concept_synthesis_task(event_type: str, payload: dict):
    task_id = process_concept_synthesis_task.request.id
    file_id = payload.get('file_id')
    chunk_payload = payload.get('chunk_payload')
    agent_output = payload.get('agent_output', {})

    if file_id is None:
        logger.error(f"Task {task_id} missing 'file_id' in payload: {payload}")
        return

    json_object = json.loads(agent_output.content)
    chunk = StandardChunk.model_validate_json(chunk_payload)
    chunk.alignment = ChunkAlignment(**json_object['alignment'])
    chunk.concept = ChunkConcept(**json_object['concept'])

    create_serialized_data(
        chunk.model_dump_json(),
        ChunkDataSerializer,
        file_id=file_id
    )

    # TODO: 2. Call the embedding model
    # TODO: 3. Write to vector database (OpenSearch / Pinecone)

    redis_client = get_raw_redis_client("default")
    remaining = redis_client.decr(f"file:{file_id}:pending_chunks")
    if remaining == 0:
        mark_file_status(file_id, ProcessStatus.SUCCESS)

@celery_app.task(name=ProcessTriplesExtractor.name, ignore_result=True)
def process_triples_extractor_task(event_type: str, payload: dict):
    task_id = process_triples_extractor_task.request.id
    file_id = payload.get('file_id')
    chunk_payload = payload.get('chunk_payload')
    agent_output = payload.get('agent_output', {})

    if file_id is None:
        logger.error(f"Task {task_id} missing 'file_id' in payload: {payload}")
        return

    chunk = StandardChunk.model_validate_json(chunk_payload)
    chunk.keywords = ChunkKeywords.model_validate_json(agent_output.content)

    semantic_filter_pipeline = FilterPipeline()
    semantic_filter_pipeline.add_filter(GroundedInEvidenceFilter())
    semantic_filter_pipeline.add_filter(SemanticQualityFilter())

    redis_client = get_raw_redis_client("default")
    if not semantic_filter_pipeline.process_item(chunk):
        remaining = redis_client.decr(f"file:{file_id}:pending_chunks")
        if remaining == 0:
            mark_file_status(file_id, ProcessStatus.SUCCESS)

        return

    agent_payload = payload.copy()
    next_event_payload = agent_payload | {
        'file_id': file_id,
        'chunk_payload': chunk.model_dump_json()
    }
    agent_payload |= {
        'agent_input_data': {
            'excerpt_text': chunk.evidence.excerpt_text,
        },
        'next_event_type': ProcessConceptSynthesis.name,
        'next_event_payload': next_event_payload,
        'next_event_queue': ProcessConceptSynthesis.queue,
    }

    publish_event.delay(
        event_type=AgentRequest.name,
        payload=agent_payload,
        queue=AgentRequest.queue
    )


@celery_app.task(name=ProcessRepositoryChunk.name, ignore_result=True)
def process_repository_chunk_task(event_type: str, payload: dict):
    task_id = process_repository_chunk_task.request.id
    file_id = payload.get('file_id')
    chunk_payload = payload.get('chunk_payload')

    chunk = StandardChunk.model_validate_json(chunk_payload)

    agent_config = cast(Dict, get_serialized_data(
        query={'role': 'ExtractKeywordsAgent'},
        model_class=AgentConfig,
        serializer_class=AgentConfigSerializer,
        many=False
    ))

    agent_payload = agent_config.copy()
    next_event_payload = agent_payload | {
        'file_id': file_id,
        'chunk_payload': chunk_payload
    }
    agent_payload |= {
        'agent_input_data': {
            'excerpt_text': chunk.evidence.excerpt_text,
        },
        'next_event_type': ProcessTriplesExtractor.name,
        'next_event_payload': next_event_payload,
        'next_event_queue': ProcessTriplesExtractor.queue,
    }

    publish_event.delay(
        event_type=AgentRequest.name,
        payload=agent_payload,
        queue=AgentRequest.queue
    )

@celery_app.task(name=ProcessRepositoryFile.name, ignore_result=True)
def process_repository_file_task(event_type: str, payload: dict):
    """
    Background Celery task to parse, chunk, and embed a repository file.
    """
    task_id = process_repository_file_task.request.id
    file_id = payload.get('file_id', None)
    static_rule_filter = StaticRuleFilter()
    logger.info(f"Received task {task_id} to process file with ID: {file_id}")

    if file_id is None:
        logger.error(f"Task {task_id} missing 'file_id' in payload: {payload}")
        return

    try:
        file_record = RepositoryFile.objects.get(id=file_id)

        file_record.status = ProcessStatus.PROCESSING
        file_record.save(update_fields=['status'])

        logger.info(f"Starting background processing for file: {file_record.file_name} (ID: {file_id})")

        storage_service = FileStorageService()
        if file_record.file_path is None:
            raise ValueError(f"RepositoryFile {file_id} has no file path")

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

        redis_client = get_raw_redis_client("default")
        redis_client.set(f"file:{file_id}:pending_chunks", len(chunks))
        for chunk in chunks:
            if not static_rule_filter.passes(chunk):
                remaining = redis_client.decr(f"file:{file_id}:pending_chunks")
                if remaining == 0:
                    file_record.status = ProcessStatus.SUCCESS
                    file_record.save(update_fields=['status'])

                continue

            publish_event.delay(
                event_type=ProcessRepositoryChunk.name,
                payload={
                    'file_id': file_id,
                    'chunk_payload': chunk.model_dump_json()
                },
                queue=ProcessRepositoryChunk.queue
            )

        logger.info(f"File {file_id} split into {len(chunks)} chunks and dispatched successfully.")
    except RepositoryFile.DoesNotExist:
        logger.error(f"RepositoryFile with ID {file_id} not found.")
    except Exception as exc:
        logger.error(f"Error processing file {file_id}: {exc}")
        try:
            mark_file_status(file_id, ProcessStatus.ERROR)
        except Exception:
            pass

        raise process_repository_file_task.retry(exc=exc, countdown=60)
