import re

from agents.models import AgentConfig, DefaultAgentConfig
from django.db import transaction


@transaction.atomic
def initialize_default_agents_for_project(project_id) -> list[AgentConfig]:
    """
    Copies all default agent templates from DefaultAgentConfig to create
    project-scoped AgentConfig instances tied directly via ForeignKey.
    """
    default_configs = DefaultAgentConfig.objects.all()
    created_agents = []

    for default_cfg in default_configs:
        # Use update_or_create to uphold idempotency based on (project, role)
        agent_config, _ = AgentConfig.objects.update_or_create(
            project_id=project_id,
            role=default_cfg.role,
            defaults={
                "name": re.sub(r"(?<!^)(?=[A-Z])", " ", default_cfg.role),
                "purpose": default_cfg.purpose,
                "system_prompt": default_cfg.system_prompt,
                "prompt_template": default_cfg.prompt_template,
                "template_variables": default_cfg.template_variables,
                "output_schema": default_cfg.output_schema,
                "output_format": default_cfg.output_format,
                "llm_parameters": default_cfg.llm_parameters,
            }
        )
        created_agents.append(agent_config)

    return created_agents
