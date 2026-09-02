from agents.utils import initialize_default_agents_for_project
from django.db import transaction
from embeddings.utils import initialize_default_embeddings_for_project


@transaction.atomic
def initialize_project_defaults(project_id):
    agents = initialize_default_agents_for_project(project_id)
    embedding = initialize_default_embeddings_for_project(project_id)
    return {"agents": agents, "embedding": embedding}
