from typing import TYPE_CHECKING

from core.constants import ProcessStatus
from core.models import BaseModel
from django.db import models
from repositories.constants import SupportedFileType

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


class RepositoryFile(BaseModel):
    """
    Repository Document Entity (對應 RepositoryFile 與 FileItem)
    """
    file_name = models.CharField(
        max_length=255,
        help_text='Original file name (e.g., "Q3_Procurement_Plan.pdf")'
    )
    file_size = models.CharField(
        max_length=50,
        help_text='Human-readable file size (e.g., "2.4 MB")'
    )
    file_type = models.CharField(
        max_length=20,
        choices=SupportedFileType.choices,
        default=SupportedFileType.PDF,
        help_text="File format extension"
    )
    status = models.CharField(
        max_length=20,
        choices=ProcessStatus.choices,
        default=ProcessStatus.IDLE,
        help_text="Processing status of the file"
    )

    if TYPE_CHECKING:
        chunks: RelatedManager['ChunkData']

    class Meta:
        db_table = 'repository_files'
        ordering = ['-updated_at']
        verbose_name = 'Repository File'
        verbose_name_plural = 'Repository Files'

    @property
    def chunk_count(self) -> int:
        return self.chunks.count()

    def __str__(self):
        return f"{self.file_name} ({self.id})"


# ----------------------------------------------------------------------
# 2. Unified Chunk Data Model
# ----------------------------------------------------------------------
class ChunkData(BaseModel):
    """
    Unified Repository Chunk Entity
    """
    file = models.ForeignKey(
        RepositoryFile,
        on_delete=models.CASCADE,
        related_name='chunks',
        db_column='file_id',
        help_text="Parent document reference"
    )

    # ------------------------------------------------------------------
    # Layer 1: Alignment & Scope Layer
    # {
    #   "targetQuestion": string,
    #   "scope": {
    #       "domain": string,
    #       "impactLevel": "strategic" | "tactical" | "operational",
    #       "boundaries": string[]
    #   }
    # }
    # ------------------------------------------------------------------
    alignment = models.JSONField(
        default=dict,
        help_text="Layer 1: Contextual target questions, scope domain, impact level, and boundaries"
    )

    # ------------------------------------------------------------------
    # Layer 2: Abstraction Layer
    # {
    #   "title": string,
    #   "description": string
    # }
    # ------------------------------------------------------------------
    concept = models.JSONField(
        default=dict,
        help_text="Layer 2: High-level concepts and structural propositions"
    )

    # ------------------------------------------------------------------
    # Layer 3: Token & Entity-Relation Layer
    # {
    #   "triples": [{"subject": "...", "predicate": "...", "object": "..."}],
    #   "tags": ["finance", "compliance"]
    # }
    # ------------------------------------------------------------------
    keywords = models.JSONField(
        default=dict,
        help_text="Layer 3: Bound semantic triples (Subject-Predicate-Object) and thematic tags"
    )

    # ------------------------------------------------------------------
    # Layer 4: Fact & Evidence Layer
    # {
    #   "excerptText": string,
    #   "location": string
    # }
    # ------------------------------------------------------------------
    evidence = models.JSONField(
        default=dict,
        help_text="Layer 4: Exact verbatim excerpt text and source location"
    )

    class Meta:
        db_table = 'repository_chunks'
        verbose_name = 'Chunk Data'
        verbose_name_plural = 'Chunk Data'

    def __str__(self):
        return f"Chunk {self.id} (File: {self.id})"
