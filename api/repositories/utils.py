import logging
from typing import Any, Dict, List, Optional

from auraflux_core.rag.chunkers.base import BaseChunker
from auraflux_core.rag.chunkers.paragraph_chunker import \
    ParagraphDynamicChunker
from auraflux_core.rag.parsers.txt_parser import TXTParser
from core.constants import ProcessStatus
from repositories.constants import SupportedFileType
from repositories.models import RepositoryFile
from services.opensearch import (OpenSearchSchemaFactory, OpenSearchService,
                                 get_opensearch_client)

logger = logging.getLogger(__name__)


def get_chunker(
    chunker_type: Optional[str] = None,
    **kwargs
) -> BaseChunker:
    """
    Factory method to retrieve a chunker instance.
    Defaults to ParagraphDynamicChunker if type is not specified or unknown.

    :param chunker_type: Identifier string for chunker algorithm (e.g., 'paragraph', 'token')
    :param kwargs: Additional parameters passed to chunker initialization
    :return: An instance of BaseChunker
    """
    if not chunker_type or chunker_type.lower() in ("paragraph", "default"):
        return ParagraphDynamicChunker(**kwargs)

    # if chunker_type.lower() == "token":
    #     return TokenChunker(**kwargs)

    return ParagraphDynamicChunker(**kwargs)

def get_parser_by_file_type(file_type: str):
    """
    Directly select parser instance based on RepositoryFile.file_type (SupportedFileType).
    """
    if file_type == SupportedFileType.TXT:
        return TXTParser()
    # elif file_type == SupportedFileType.PDF:
    #     return PDFParser()
    # elif file_type == SupportedFileType.DOCX:
    #     return DOCXParser()
    else:
        raise ValueError(f"Unsupported SupportedFileType: {file_type}")

def mark_file_status(file_record_id: str, status: ProcessStatus):
    file_record = RepositoryFile.objects.get(id=file_record_id)
    file_record.status = status
    file_record.save(update_fields=['status'])

def decrement_pending_chunks(file_id: str, redis_client) -> None:
    """Decrement the pending chunks count for a given file."""
    remaining = redis_client.decr(f"file:{file_id}:pending_chunks")
    if remaining == 0:
        mark_file_status(file_id, ProcessStatus.SUCCESS)

def setup_opensearch():
    opensearch_service = OpenSearchService(client=get_opensearch_client())
    pipeline_schema = OpenSearchSchemaFactory.build_create_pipeline_schema(
        pipeline_id="rrf_question_oriented"
    )
    opensearch_service.ensure_search_pipeline_exists(pipeline_schema)

def sync_chunk_to_opensearch(
    file_id: str,
    chunk_id: str,
    chunk_data: Dict[str, Any],
    question_vector: List[float],
    concept_vector: List[float],
    evidence_vector: List[float],
) -> bool:
    """Syncs a single chunk document with its generated vectors to OpenSearch.

    Handles project retrieval, index initialization (if missing), document
    payload assembly, and bulk indexing.
    """
    try:
        file_obj = RepositoryFile.objects.select_related("project").get(id=file_id)
        project = file_obj.project

        opensearch_service = OpenSearchService(client=get_opensearch_client())

        dimension = len(question_vector)
        create_index_schema = OpenSearchSchemaFactory.build_create_index_schema(
            project=project,
            dimension=dimension
        )
        opensearch_service.ensure_index_exists(create_index_schema)

        concept = chunk_data.get("concept") or {}
        concept_title = concept.get("title", "") if isinstance(concept, dict) else getattr(concept, "title", "")

        opensearch_doc = {
            "chunk_id": str(chunk_id),
            "file_id": str(file_id),
            "project_id": str(project.id),
            "target_question": chunk_data.get("question", ""),
            "concept_title": concept_title,
            "evidence_text": chunk_data.get("evidence", ""),
            "question_vector": question_vector,
            "concept_vector": concept_vector,
            "evidence_vector": evidence_vector,
        }

        sync_schema = OpenSearchSchemaFactory.build_sync_schema(
            project=project,
            chunk_documents=[opensearch_doc],
            id_field="chunk_id"
        )

        success_count, errors = opensearch_service.sync_bulk(sync_schema)

        if errors:
            logger.error(f"Failed to sync chunk {chunk_id} to OpenSearch: {errors}")
            return False

        logger.info(f"Successfully synced chunk {chunk_id} to OpenSearch.")
        return True

    except RepositoryFile.DoesNotExist:
        logger.error(f"Failed to sync chunk {chunk_id}: File {file_id} not found in database.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error syncing chunk {chunk_id} to OpenSearch: {e}", exc_info=True)
        raise e
