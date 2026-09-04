import logging
from typing import Any, Dict, List, Tuple

from opensearchpy import OpenSearch, helpers

from .schemas import (OpenSearchCreateIndexSchema,
                      OpenSearchCreatePipelineSchema,
                      OpenSearchDeleteByFileSchema, OpenSearchDeleteSchema,
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
                "_routing": {
                    "required": getattr(schema, "is_pool_mode", True)
                },
                "properties": {
                    # --------------------------------------------------------
                    # 1. Tenant & Identifier Metadata
                    # --------------------------------------------------------
                    "project_id": {
                        "type": "keyword"
                    },
                    "file_id": {
                        "type": "keyword"
                    },
                    "chunk_id": {
                        "type": "keyword"
                    },

                    # --------------------------------------------------------
                    # 2. Text Search Fields (BM25 Lexical Matching)
                    # --------------------------------------------------------
                    "target_question": {
                        "type": "text"
                    },
                    "concept_title": {
                        "type": "text"
                    },
                    # Object mapping structure aligned with ChunkEvidence payload
                    "evidence_text": {
                        "properties": {
                            "excerptText": {
                                "type": "text"
                            },
                            "location": {
                                "type": "text",
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 256
                                    }
                                }
                            }
                        }
                    },

                    # --------------------------------------------------------
                    # 3. Dense Multi-Vector Fields (FAISS Engine)
                    # --------------------------------------------------------
                    "question_vector": {
                        "type": "knn_vector",
                        "dimension": schema.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "faiss"
                        }
                    },
                    "concept_vector": {
                        "type": "knn_vector",
                        "dimension": schema.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "faiss"
                        }
                    },
                    "evidence_vector": {
                        "type": "knn_vector",
                        "dimension": schema.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "faiss"
                        }
                    }
                }
            }
        }

        try:
            if self.client.indices.exists(index=schema.index_name):
                logger.warning(f"Index '{schema.index_name}' already exists.")
                return False

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

    # ------------------------------------------------------------------
    # Pipeline Management Operations
    # ------------------------------------------------------------------
    def create_search_pipeline(self, schema: OpenSearchCreatePipelineSchema) -> bool:
        """Creates or updates an OpenSearch search pipeline."""
        try:
            self.client.search_pipeline.put(
                id=schema.pipeline_id,
                body=schema.to_pipeline_body()
            )
            logger.info(f"Successfully created search pipeline '{schema.pipeline_id}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create search pipeline '{schema.pipeline_id}': {e}")
            return False

    def ensure_search_pipeline_exists(self, schema: OpenSearchCreatePipelineSchema) -> bool:
        """Idempotently ensures the target search pipeline exists."""
        try:
            self.client.search_pipeline.get(id=schema.pipeline_id)
            return True
        except Exception:
            return self.create_search_pipeline(schema)

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

    def delete_by_file_ids(self, schema: OpenSearchDeleteByFileSchema) -> int:
        """Deletes documents matching the given file_ids using delete_by_query."""
        if not schema.file_ids:
            return 0

        terms_query = {"terms": {"file_id.keyword": schema.file_ids}}

        if schema.project_id:
            query_body = {
                "conflicts": "proceed",
                "query": {
                    "bool": {
                        "must": [terms_query],
                        "filter": [{"term": {"project_id.keyword": schema.project_id}}]
                    }
                }
            }
        else:
            query_body = {
                "conflicts": "proceed",
                "query": terms_query
            }

        params = {}
        if schema.routing:
            params["routing"] = schema.routing

        try:
            response = self.client.delete_by_query(
                index=schema.index_name,
                body=query_body,
                params=params
            )
            deleted_count = response.get("deleted", 0)
            logger.info(
                f"Successfully deleted {deleted_count} docs for file_ids "
                f"{schema.file_ids} in index '{schema.index_name}'"
            )
            return deleted_count
        except Exception as e:
            logger.error(
                f"Failed delete_by_query for file_ids in index '{schema.index_name}': {e}"
            )
            return 0

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
