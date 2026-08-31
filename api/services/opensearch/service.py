import logging
from typing import Any, Dict, List, Tuple

from opensearchpy import OpenSearch, helpers

from .schemas import (OpenSearchCreateIndexSchema, OpenSearchDeleteSchema,
                      OpenSearchSearchSchema, OpenSearchSyncSchema)

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Infrastructure driver wrapper executing low-level search and bulk operations for OpenSearch."""

    def __init__(self, client: OpenSearch):
        self.client = client

    def search(self, schema: OpenSearchSearchSchema) -> List[Dict[str, Any]]:
        """Executes a search request using the provided OpenSearchSearchSchema."""
        search_params = {}
        if schema.search_pipeline:
            search_params["search_pipeline"] = schema.search_pipeline
        if schema.routing:
            search_params["routing"] = schema.routing

        response = self.client.search(
            index=schema.index_name,
            body=schema.body,
            params=search_params
        )
        return response["hits"]["hits"]

    # ------------------------------------------------------------------
    # Index Management Operations
    # ------------------------------------------------------------------
    def create_index(self, schema: OpenSearchCreateIndexSchema) -> bool:
        """Creates an OpenSearch index configured for kNN vector search."""
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": schema.shards,
                    "number_of_replicas": schema.replicas,
                }
            },
            "mappings": {
                "properties": {
                    "project_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "target_question": {"type": "text"},
                    "concept_title": {"type": "text"},
                    "evidence_text": {"type": "text"},
                    "question_vector": {
                        "type": "knn_vector",
                        "dimension": schema.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "concept_vector": {
                        "type": "knn_vector",
                        "dimension": schema.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "evidence_vector": {
                        "type": "knn_vector",
                        "dimension": schema.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    }
                }
            }
        }

        try:
            self.client.indices.create(index=schema.index_name, body=index_body)
            logger.info(f"Successfully created index '{schema.index_name}' with dimension {schema.dimension}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index '{schema.index_name}': {e}")
            return False

    def ensure_index_exists(self, schema: OpenSearchCreateIndexSchema) -> bool:
        """Idempotently ensures the target index exists, creating it if necessary."""
        try:
            if not self.client.indices.exists(index=schema.index_name):
                return self.create_index(schema)
            return True
        except Exception as e:
            logger.error(f"Error checking index existence for '{schema.index_name}': {e}")
            return False

    def delete_by_ids(self, schema: OpenSearchDeleteSchema) -> Tuple[int, List[Any]]:
        """Deletes multiple documents by their IDs using bulk API."""
        actions = []
        for doc_id in schema.doc_ids:
            action = {
                "_op_type": "delete",
                "_index": schema.index_name,
                "_id": str(doc_id)
            }
            if schema.routing:
                action["_routing"] = schema.routing

            actions.append(action)

        success_count, errors = helpers.bulk(
            self.client,
            actions,
            raise_on_error=False
        )

        if errors:
            logger.error(f"OpenSearch bulk delete errors on index '{schema.index_name}': {errors}")

        return success_count, errors

    def delete_by_id(self, schema: OpenSearchDeleteSchema) -> bool:
        """Deletes a single document by its ID."""
        if not schema.doc_ids:
            return False

        target_id = schema.doc_ids[0]
        params = {}
        if schema.routing:
            params["routing"] = schema.routing

        try:
            response = self.client.delete(
                index=schema.index_name,
                id=target_id,
                params=params
            )
            return response.get("result") == "deleted"
        except Exception as e:
            logger.error(f"Failed to delete document {target_id} from {schema.index_name}: {e}")
            return False

    def sync_bulk(self, schema: OpenSearchSyncSchema) -> Tuple[int, List[Any]]:
        """Executes bulk indexing operations using the provided OpenSearchSyncSchema."""
        actions = []
        for doc in schema.documents:
            doc_id = doc.get(schema.id_field)
            action = {
                "_op_type": "index",
                "_index": schema.index_name,
                "_source": doc
            }
            if doc_id:
                action["_id"] = str(doc_id)
            if schema.routing:
                action["_routing"] = schema.routing

            actions.append(action)

        success_count, errors = helpers.bulk(
            self.client,
            actions,
            raise_on_error=False
        )

        if errors:
            logger.error(f"OpenSearch bulk sync errors on index '{schema.index_name}': {errors}")

        return success_count, errors
