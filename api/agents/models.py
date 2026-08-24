import uuid

from agents.constants import AgentOutputFormat
from core.models import BaseModel
from django.db import models


class AgentConfig(BaseModel):
    """
    Defines the specific role, behavior, and LLM parameters for an agent type
    (e.g., 'Dichotomy Suggester', 'Scope Summarizer').
    """
    name = models.CharField(
        max_length=100,
    )

    role = models.CharField(
        max_length=100,
        help_text="The unique name used to identify this agent role (e.g., 'Dichotomy Suggester')."
    )

    # Core behavior settings
    system_prompt = models.TextField(
        help_text="The instruction set given to the LLM to define its persona and task."
    )

    # Stores the full prompt text with placeholders (e.g., {{final_question_draft}})
    prompt_template = models.TextField(
        help_text="The full template text used to render the final prompt, containing all static text and {{variable}} placeholders."
    )

    # Defines what data needs to be fetched for the template placeholders.
    template_variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="A dictionary defining the dynamic variables required by the prompt_template and their data source/type (e.g., {'final_question_draft': 'DB_FACTS', 'latest_user_input': 'CURRENT_TURN'})."
    )

    output_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="The JSON schema defining the required output structure for the LLM response."
    )

    output_format = models.CharField(
        max_length=20,
        choices=AgentOutputFormat.choices,
        default=AgentOutputFormat.TEXT,
        help_text="The expected format of the LLM's output (e.g., 'TEXT', 'JSON')."
    )

    llm_parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Specific runtime parameters for the LLM call (e.g., temperature, top_p, max_tokens)."
    )

    provider_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        help_text="The ID of the LLM provider configuration used for this agent."
    )

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='agents',
        help_text="The project this agent configuration belongs to."
    )

    class Meta:
        verbose_name = "Agent Configuration"
        verbose_name_plural = "Agent Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'role'],
                name='unique_agent_role_per_project'
            )
        ]

    def __str__(self):
        return self.name


class DefaultAgentConfig(BaseModel):
    """
    Defines the default role, behavior, and LLM parameters for an agent type
    """
    role = models.CharField(
        max_length=100,
        unique=True,
        help_text="The unique name used to identify this agent role (e.g., 'Dichotomy Suggester')."
    )

    # Core behavior settings
    system_prompt = models.TextField(
        help_text="The instruction set given to the LLM to define its persona and task."
    )

    # Stores the full prompt text with placeholders (e.g., {{final_question_draft}})
    prompt_template = models.TextField(
        help_text="The full template text used to render the final prompt, containing all static text and {{variable}} placeholders."
    )

    # Defines what data needs to be fetched for the template placeholders.
    template_variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="A dictionary defining the dynamic variables required by the prompt_template and their data source/type (e.g., {'final_question_draft': 'DB_FACTS', 'latest_user_input': 'CURRENT_TURN'})."
    )

    output_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="The JSON schema defining the required output structure for the LLM response."
    )

    output_format = models.CharField(
        max_length=20,
        choices=AgentOutputFormat.choices,
        default=AgentOutputFormat.TEXT,
        help_text="The expected format of the LLM's output (e.g., 'TEXT', 'JSON')."
    )

    llm_parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Specific runtime parameters for the LLM call (e.g., temperature, top_p, max_tokens)."
    )

    class Meta:
        verbose_name = "Default Agent Configuration"
        verbose_name_plural = "Default Agent Configurations"

    def __str__(self):
        return self.role
