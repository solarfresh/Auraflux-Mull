from adrf.serializers import ModelSerializer
from embeddings.models import EmbeddingConfig
from rest_framework import serializers


class EmbeddingConfigSerializer(ModelSerializer):
    projectId = serializers.UUIDField(source='project_id', read_only=True)
    providerId = serializers.UUIDField(source='provider_id', read_only=False)
    modelFamilyId = serializers.UUIDField(source='model_family_id', read_only=False)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    name = serializers.CharField(required=False, allow_blank=True)
    parameters = serializers.JSONField(default=dict, required=False)

    class Meta:
        model = EmbeddingConfig
        fields = (
            'id',
            'projectId',
            'providerId',
            'modelFamilyId',
            'createdAt',
            'updatedAt',
            'name',
            'parameters',
        )
        read_only_fields = ('id', 'createdAt', 'updatedAt')
