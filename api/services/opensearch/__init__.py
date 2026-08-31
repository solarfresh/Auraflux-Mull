"""OpenSearch Integration Module.

Provides schemas, factories, and services for performing query, bulk indexing,
and document deletion operations against OpenSearch.
"""

from .schemas import (
    OpenSearchCreateIndexSchema,
    OpenSearchDeleteSchema,
    OpenSearchSearchSchema,
    OpenSearchSyncSchema,
    OpenSearchSchemaFactory,
)
from .service import OpenSearchService

__all__ = [
    # Schemas & Factory
    "OpenSearchSearchSchema",
    "OpenSearchCreateIndexSchema",
    "OpenSearchSyncSchema",
    "OpenSearchDeleteSchema",
    "OpenSearchSchemaFactory",
    # Infrastructure Service
    "OpenSearchService",
]
