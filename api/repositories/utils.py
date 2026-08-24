import logging
from typing import Optional

from auraflux_core.rag.chunkers.base import BaseChunker
from auraflux_core.rag.chunkers.paragraph_chunker import \
    ParagraphDynamicChunker
from auraflux_core.rag.parsers.txt_parser import TXTParser
from core.constants import ProcessStatus
from repositories.constants import SupportedFileType
from repositories.models import RepositoryFile

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
