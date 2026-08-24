from adrf.serializers import ModelSerializer
from agents.models import AgentConfig
from rest_framework import serializers


class AgentConfigSerializer(ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    name = serializers.CharField(required=False, allow_blank=True)
    purpose = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, allow_blank=True)
    systemPrompt = serializers.CharField(source='system_prompt', required=False, allow_blank=True)
    promptTemplate = serializers.CharField(source='prompt_template', required=False, allow_blank=True)
    templateVariables = serializers.JSONField(source='template_variables', default={})
    outputSchema = serializers.JSONField(source='output_schema', default={})
    llmParameters = serializers.JSONField(source='llm_parameters', default={})

    class Meta:
        model = AgentConfig
        fields = (
            'id',
            'createdAt',
            'updatedAt',
            'name',
            'purpose',
            'role',
            'systemPrompt',
            'promptTemplate',
            'templateVariables',
            'outputSchema',
            'llmParameters'
        )
        read_only_fields = ('id', 'createdAt', 'updatedAt')
