from adrf.serializers import ModelSerializer
from agents.models import AgentConfig
from rest_framework import serializers


class AgentConfigSerializer(ModelSerializer):
    projectId = serializers.UUIDField(source='project_id', read_only=True)
    providerId = serializers.UUIDField(source='provider_id', read_only=False)
    modelFamilyId = serializers.UUIDField(source='model_family_id', read_only=False)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    name = serializers.CharField(required=False, allow_blank=True)
    purpose = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, allow_blank=True)
    systemPrompt = serializers.CharField(source='system_prompt', required=False, allow_blank=True)
    promptTemplate = serializers.CharField(source='prompt_template', required=False, allow_blank=True)
    templateVariables = serializers.JSONField(source='template_variables', default={})
    outputFormat = serializers.CharField(source='output_format', required=False, allow_blank=True)
    outputSchema = serializers.JSONField(source='output_schema', default={})
    llmParameters = serializers.JSONField(source='llm_parameters', default={})

    class Meta:
        model = AgentConfig
        fields = (
            'id',
            'projectId',
            'providerId',
            'modelFamilyId',
            'createdAt',
            'updatedAt',
            'name',
            'purpose',
            'role',
            'systemPrompt',
            'promptTemplate',
            'templateVariables',
            'outputFormat',
            'outputSchema',
            'llmParameters'
        )
        read_only_fields = ('id', 'createdAt', 'updatedAt')
