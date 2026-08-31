"""OpenSearch Integration Module.

Provides schemas, factories, and services for performing query, bulk indexing,
and document deletion operations against OpenSearch.
"""

from .client import get_opensearch_client
from .schemas import (
    OpenSearchCreateIndexSchema,
    OpenSearchDeleteSchema,
    OpenSearchSearchSchema,
    OpenSearchSyncSchema,
    OpenSearchSchemaFactory,
)
from .service import OpenSearchService

__all__ = [
    "get_opensearch_client",
    # Schemas & Factory
    "OpenSearchSearchSchema",
    "OpenSearchCreateIndexSchema",
    "OpenSearchSyncSchema",
    "OpenSearchDeleteSchema",
    "OpenSearchSchemaFactory",
    # Infrastructure Service
    "OpenSearchService",
]
