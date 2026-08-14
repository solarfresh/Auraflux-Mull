import logging

from adrf.serializers import ModelSerializer
from core.constants import EntityStatus
from rest_framework import serializers
from projects.models import Project

logger = logging.getLogger(__name__)


class ProjectSerializer(ModelSerializer):
    status = serializers.ChoiceField(
        choices=EntityStatus.choices,
        required=False,
        help_text="The current status of the project entity"
    )
    createdAt = serializers.DateTimeField(
        source='created_at',
        read_only=True,
        help_text="The timestamp when the project was created"
    )
    updatedAt = serializers.DateTimeField(
        source='updated_at',
        read_only=True,
        help_text="The timestamp when the project was last updated"
    )

    class Meta:
        model = Project
        fields = [
            'id',
            'name',
            'description',
            'status',
            'tags',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['id', 'createdAt', 'updatedAt']
