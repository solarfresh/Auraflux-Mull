import uuid

from core.constants import EntityStatus
from core.models import BaseModel
from django.contrib.auth import get_user_model
from django.db import models


class Project(BaseModel):
    """
    Project model representing the structure defined in the TypeScript interface.
    """
    # Project name
    name = models.CharField(max_length=255)

    # Optional description
    description = models.TextField(blank=True, null=True)

    # Status field using the TextChoices defined above
    status = models.CharField(
        max_length=20,
        choices=EntityStatus.choices,
        default=EntityStatus.DRAFT
    )

    # Tags as a JSONField (PostgreSQL) or simple text for simplicity
    # If using JSONField, it supports list storage natively
    tags = models.JSONField(default=list, blank=True)

    user_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        help_text="The ID of the user owning this project."
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'project'
        verbose_name_plural = 'projects'

    def __str__(self):
        return self.name
