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
from django.db import transaction
from embeddings.models import EmbeddingConfig
from embeddings.serializers import EmbeddingConfigSerializer
from messaging.constants import (AgentRequest, EmbeddingRequest,
                                 ProcessConceptSynthesis,
                                 ProcessRepositoryChunk, ProcessRepositoryFile,
                                 ProcessTriplesExtractor, ProcessVectorStorage)
from messaging.tasks import publish_event
from repositories.models import RepositoryFile
from repositories.serializers import ChunkDataSerializer
from repositories.utils import (get_chunker, get_parser_by_file_type,
                                mark_file_status, sync_chunk_to_opensearch)
from services.semaphore import get_raw_redis_client
from services.storage import FileStorageService

logger = logging.getLogger(__name__)


@celery_app.task(name=ProcessConceptSynthesis.name, ignore_result=True)
def process_concept_synthesis_task(event_type: str, payload: dict):
    task_id = process_concept_synthesis_task.request.id
    file_id = payload.get('file_id')
    chunk_payload = payload.get('chunk_payload', None)
    agent_output = payload.get('agent_output', None)
    redis_client = get_raw_redis_client("default")

    if file_id is None:
        logger.error(f"Task {task_id} missing 'file_id' in payload: {payload}")
        return

    if chunk_payload is None:
        logger.error(f"Task {task_id} missing 'chunk_payload' in payload: {payload}")
        mark_file_status(file_id, ProcessStatus.ERROR)
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    if agent_output is None:
        logger.error(f"Task {task_id} missing 'agent_output' in payload: {payload}")
        mark_file_status(file_id, ProcessStatus.ERROR)
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    try:
        json_object = json.loads(agent_output)
        chunk = StandardChunk.model_validate_json(chunk_payload)
        chunk.alignment = ChunkAlignment(**json_object['alignment'])
        chunk.concept = ChunkConcept(**json_object['concept'])
    except Exception as e:
        logger.error(f"Task {task_id} failed to parse chunk or agent_output: {e}")
        mark_file_status(file_id, ProcessStatus.ERROR)
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    try:
        embedding_config = cast(Dict, get_serialized_data(
            query={'role': 'SearchEmbedding'},
            model_class=EmbeddingConfig,
            serializer_class=EmbeddingConfigSerializer,
            many=False
        ))
    except EmbeddingConfig.DoesNotExist:
        logger.error(f"Task {task_id}: EmbeddingConfig with role 'SearchEmbedding' not found.")
        mark_file_status(file_id, ProcessStatus.ERROR)
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    embedding_config_params = embedding_config.get('parameters', {})

    # Extract and assemble texts based on the StandardChunk model
    target_question = chunk.alignment.targetQuestion if chunk.alignment else ""
    concept_text = f"{chunk.concept.title} {chunk.concept.description}".strip() if chunk.concept else ""
    evidence_text = chunk.evidence.excerptText if chunk.evidence else ""

    # Input array ordered strictly for multi-vector mapping: [Question, Concept, Evidence]
    input_texts = [
        target_question,
        concept_text,
        evidence_text
    ]

    # Next event context payload
    next_event_payload = {
        'file_id': file_id,
        'chunk_id': chunk.id,
        'chunk_payload': chunk.model_dump_json(),
    }

    # Construct Embedding Event Payload matching get_embedding_response args
    embedding_payload = {
        'provider_id': embedding_config.get('providerId', None),
        'embedding_name': embedding_config.get('name', ''),
        'embedding_role': embedding_config.get('role', ''),
        'parameters': embedding_config_params,
        'input_text': input_texts,
        'use_batch': payload.get('is_premium', True),
        'next_event_type': ProcessVectorStorage.name,
        'next_event_payload': next_event_payload,
        'next_event_queue': ProcessVectorStorage.queue,
    }

    # Dispatch event to the Embedding Task Queue
    publish_event.delay(
        event_type=EmbeddingRequest.name,
        payload=embedding_payload,
        queue=EmbeddingRequest.queue
    )

@celery_app.task(name=ProcessTriplesExtractor.name, ignore_result=True)
def process_triples_extractor_task(event_type: str, payload: dict):
    task_id = process_triples_extractor_task.request.id
    file_id = payload.get('file_id')
    chunk_payload = payload.get('chunk_payload')
    agent_output = payload.get('agent_output', {})
    redis_client = get_raw_redis_client("default")

    if chunk_payload is None:
        logger.error(f"Task {task_id} missing 'chunk_payload' in payload: {payload}")
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    if file_id is None:
        logger.error(f"Task {task_id} missing 'file_id' in payload: {payload}")
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    json_object = json.loads(agent_output)
    chunk = StandardChunk.model_validate_json(chunk_payload)
    chunk.keywords = ChunkKeywords(**json_object)

    semantic_filter_pipeline = FilterPipeline()
    semantic_filter_pipeline.add_filter(GroundedInEvidenceFilter())
    semantic_filter_pipeline.add_filter(SemanticQualityFilter())

    redis_client = get_raw_redis_client("default")
    if not semantic_filter_pipeline.process_item(chunk):
        remaining = redis_client.decr(f"file:{file_id}:pending_chunks")
        if remaining == 0:
            mark_file_status(file_id, ProcessStatus.SUCCESS)

        return

    agent_config = cast(Dict, get_serialized_data(
        query={'role': 'SynthesizeConceptAgent'},
        model_class=AgentConfig,
        serializer_class=AgentConfigSerializer,
        many=False
    ))

    agent_payload = {
        'provider_id': agent_config.get('providerId', None),
        'agent_name': agent_config.get('name', None),
        'agent_role': agent_config.get('role', None),
        'system_prompt': agent_config.get('systemPrompt', None),
        'llm_parameters': agent_config.get('llmParameters', None),
        'prompt_template': agent_config.get('promptTemplate', None),
        'template_variables': agent_config.get('templateVariables', None),
        'output_format': agent_config.get('outputFormat', None),
    }

    next_event_payload = agent_payload | {
        'file_id': file_id,
        'chunk_payload': chunk.model_dump_json()
    }
    agent_payload |= {
        'agent_input_data': {
            'excerpt_text': chunk.evidence.excerptText,
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

@celery_app.task(name=ProcessVectorStorage.name, ignore_result=True)
def process_vector_storage_task(event_type: str, payload: dict):
    task_id = process_vector_storage_task.request.id
    file_id = payload.get('file_id')
    chunk_payload = payload.get('chunk_payload', None)
    embedding_output = payload.get('embedding_output', [])
    redis_client = get_raw_redis_client("default")

    # 1. Basic validation
    if chunk_payload is None:
        logger.error(f"Task {task_id} missing 'chunk_payload' in payload: {payload}")
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    if file_id is None:
        logger.error(f"Task {task_id} missing 'file_id' in payload: {payload}")
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    # Validate output vector completeness to prevent IndexError
    if not isinstance(embedding_output, list) or len(embedding_output) < 3:
        logger.error(f"Task {task_id} received incomplete embedding_output: {embedding_output}")
        mark_file_status(file_id, ProcessStatus.ERROR)
        redis_client.decr(f"file:{file_id}:pending_chunks")
        return

    # Extract vectors safely
    question_vector = embedding_output[0]
    concept_vector = embedding_output[1]
    evidence_vector = embedding_output[2]

    # 2. Parse chunk and build standard JSON structure
    chunk = StandardChunk.model_validate_json(chunk_payload)

    chunk_data = chunk.model_dump(
        mode="json",
        exclude={'id', 'fileId'}
    )
    chunk_data['fileId'] = file_id

    try:
        # 3. Database operation inside atomic transaction
        with transaction.atomic():
            create_serialized_data(
                chunk_data,
                ChunkDataSerializer
            )

        # 4. External Vector DB syncing outside DB transaction
        sync_chunk_to_opensearch(
            file_id=file_id,
            chunk_id=chunk.id,
            chunk_data=chunk_data,
            question_vector=question_vector,
            concept_vector=concept_vector,
            evidence_vector=evidence_vector,
        )

        # 5. Non-relational Redis operations outside DB transaction
        remaining = redis_client.decr(f"file:{file_id}:pending_chunks")
        if remaining == 0:
            mark_file_status(file_id, ProcessStatus.SUCCESS)

    except Exception as e:
        logger.error(f"Task {task_id} failed during vector storage processing: {str(e)}", exc_info=True)
        mark_file_status(file_id, ProcessStatus.ERROR)
        redis_client.decr(f"file:{file_id}:pending_chunks")
        raise e

@celery_app.task(name=ProcessRepositoryChunk.name, ignore_result=True)
def process_repository_chunk_task(event_type: str, payload: dict):
    task_id = process_repository_chunk_task.request.id
    file_id = payload.get('file_id')
    chunk_payload = payload.get('chunk_payload')

    if chunk_payload is None:
        logger.error(f"Task {task_id} missing 'chunk_payload' in payload: {payload}")
        return

    chunk = StandardChunk.model_validate_json(chunk_payload)

    agent_config = cast(Dict, get_serialized_data(
        query={'role': 'ExtractKeywordsAgent'},
        model_class=AgentConfig,
        serializer_class=AgentConfigSerializer,
        many=False
    ))

    agent_payload = {
        'provider_id': agent_config.get('providerId', None),
        'agent_name': agent_config.get('name', None),
        'agent_role': agent_config.get('role', None),
        'system_prompt': agent_config.get('systemPrompt', None),
        'llm_parameters': agent_config.get('llmParameters', None),
        'prompt_template': agent_config.get('promptTemplate', None),
        'template_variables': agent_config.get('templateVariables', None),
        'output_format': agent_config.get('outputFormat', None),
    }

    next_event_payload = agent_payload | {
        'file_id': file_id,
        'chunk_payload': chunk_payload
    }
    agent_payload |= {
        'agent_input_data': {
            'excerpt_text': chunk.evidence.excerptText,
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
