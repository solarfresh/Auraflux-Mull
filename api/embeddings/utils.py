from django.db import transaction
from embeddings.models import DefaultEmbeddingConfig, EmbeddingConfig


@transaction.atomic
def initialize_default_embeddings_for_project(project_id) -> list[EmbeddingConfig]:
    """
    Copies all default embedding templates from DefaultEmbeddingConfig to create
    project-scoped EmbeddingConfig instances tied directly via ForeignKey and role.
    """
    default_configs = DefaultEmbeddingConfig.objects.all()
    created_embeddings = []

    for default_cfg in default_configs:
        embedding_config, _ = EmbeddingConfig.objects.update_or_create(
            project_id=project_id,
            role=default_cfg.role,
            defaults={
                "name": default_cfg.name,
            }
        )
        created_embeddings.append(embedding_config)

    return created_embeddings