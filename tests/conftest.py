import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from embeddings.models import EmbeddingConfig
from projects.models import EntityStatus, Project
from repositories.models import (ProcessStatus, RepositoryFile,
                                 SupportedFileType)

# -------------------------------------------------------------------------
# Global Environment & Third-Party Mocks
# -------------------------------------------------------------------------

def pytest_configure(config):
    """
    Hook into pytest configuration to modify Django settings dynamically before setup.
    This safely bypasses the 'logfile' handler directory dependency during tests.
    """
    from django.conf import settings

    # Check if Django settings are configured and LOGGING dict exists
    if hasattr(settings, "LOGGING") and "handlers" in settings.LOGGING:
        if "logfile" in settings.LOGGING["handlers"]:
            # Dynamically switch the file handler to a safe console output or NullHandler
            settings.LOGGING["handlers"]["logfile"] = {
                "class": "logging.StreamHandler",  # Redirect to stdout/stderr
                "formatter": "verbose" if "verbose" in settings.LOGGING.get("formatters", {}) else None
            }

# -------------------------------------------------------------------------
# API Client Fixtures (For Integration Endpoint Testing)
# -------------------------------------------------------------------------

@pytest.fixture
def authenticated_api_client(test_user):
    """
    Provides an adrf / rest_framework API Client injected with pre-verified
    credentials acting as the logged-in target user context.
    """
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client

# -------------------------------------------------------------------------
# Database Fixtures
# -------------------------------------------------------------------------

@pytest.fixture
def create_search_embedding_config():
    return EmbeddingConfig.objects.create(
        name="text-embedding-3-small",
        role="SearchEmbedding",
        parameters={
            "dimensions": 1536,
            "provider": "openai",
            "model": "text-embedding-3-small"
        }
    )

@pytest.fixture
def create_project(db):
    """
    Creates a valid Project database entry required as a ForeignKey for RepositoryFile.
    """
    return Project.objects.create(
        name="Test Synthesis Project",
        description="A project instance for task pipeline integration tests.",
        status=EntityStatus.DRAFT,
        tags=["test", "celery", "pipeline"],
        user_id=uuid.uuid4()
    )

@pytest.fixture
def create_repository_file(db, create_project):
    """
    Creates a complete RepositoryFile database entry backed by an existing Project.
    """
    return RepositoryFile.objects.create(
        file_name="test_concept_document.pdf",
        file_size="1.2 MB",
        file_type=SupportedFileType.PDF,
        status=ProcessStatus.PROCESSING,
        project=create_project,
        user_id=uuid.uuid4()
    )

@pytest.fixture
def create_embedding_config(db, create_project):
    """
    Creates a valid EmbeddingConfig entry required for concept synthesis tasks.
    """
    return EmbeddingConfig.objects.create(
        name="Text Embedding Config",
        role="SearchEmbedding",
        provider_id=uuid.uuid4(),
        parameters={"model": "text-embedding-3-small"},
        project=create_project
    )

# -------------------------------------------------------------------------
# Service Mocks (For Unit Testing Service Logic)
# -------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Mock raw Redis client instance."""
    return MagicMock()

# -------------------------------------------------------------------------
# Mock Payload Fixtures
# -------------------------------------------------------------------------

@pytest.fixture
def valid_chunk_payload(create_repository_file):
    """
    Provides a valid JSON string payload matching all required fields of StandardChunk.
    """
    chunk_data = {
        "id": str(uuid.uuid4()),
        "fileId": str(create_repository_file.id),
        "evidence": {
            "excerptText": "This section outlines the non-negotiable compliance rules for cloud storage.",
            "location": "Page 1, Section 2"
        }
    }
    return json.dumps(chunk_data)


@pytest.fixture
def valid_agent_output():
    """
    Provides a valid LLM agent JSON output payload for alignment and concept.
    """
    agent_data = {
        "alignment": {
            "targetQuestion": "What is concept synthesis?"
        },
        "concept": {
            "title": "Concept Synthesis",
            "description": "Synthesizing key insights from multiple chunks."
        }
    }
    return json.dumps(agent_data)
