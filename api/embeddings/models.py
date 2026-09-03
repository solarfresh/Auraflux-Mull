import uuid
from core.models import BaseModel
from django.db import models


class EmbeddingConfig(BaseModel):
    """
    Defines the embedding model configuration bound to a specific project.
    """
    name = models.CharField(
        max_length=100,
        default="Default Embedding",
        help_text="The display name for this embedding configuration."
    )

    role = models.CharField(
        max_length=50,
        help_text="The role or purpose of this embedding configuration (e.g., 'search', 'recommendation')."
    )

    provider_id = models.UUIDField(
        default=uuid.uuid4,
        editable=True,
        help_text="The ID of the LLM provider configuration used for embeddings."
    )

    model_family_id = models.UUIDField(
        default=uuid.uuid4,
        editable=True,
        help_text="The ID of the embedding model family used for generating vectors."
    )

    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Specific runtime parameters for the embedding model (e.g., dimensions, chunk_size)."
    )

    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='embedding',
        help_text="The project this embedding configuration belongs to."
    )

    class Meta:
        verbose_name = "Embedding Configuration"
        verbose_name_plural = "Embedding Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'role'],
                name='unique_embedding_role_per_project'
            )
        ]

    def __str__(self):
        return self.name


class DefaultEmbeddingConfig(BaseModel):
    """
    Defines the system-wide default embedding model parameters.
    Used as a baseline template during project initialization.
    """
    name = models.CharField(
        max_length=100,
        default="Default System Embedding",
        help_text="The display name for the default embedding configuration."
    )

    role = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique identifier for the embedding role (e.g., 'default_search', 'code_retrieval')."
    )

    class Meta:
        verbose_name = "Default Embedding Configuration"
        verbose_name_plural = "Default Embedding Configurations"

    def __str__(self):
        return self.name
