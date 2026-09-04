import re
from typing import Any, Dict, List, Optional

from django.core.exceptions import ObjectDoesNotExist
from pydantic import BaseModel, ConfigDict, Field


class OpenSearchSearchSchema(BaseModel):
    """Schema encapsulating parameters required for an OpenSearch query execution."""
    model_config = ConfigDict(frozen=True)

    index_name: str = Field(..., min_length=1, description="Target OpenSearch index name")
    body: Dict[str, Any] = Field(..., description="OpenSearch query DSL body")
    routing: Optional[str] = Field(default=None, description="OpenSearch routing key")
    search_pipeline: Optional[str] = Field(default=None, description="Search pipeline name")


class OpenSearchCreateIndexSchema(BaseModel):
    """Schema encapsulating configuration parameters for index creation."""
    model_config = ConfigDict(frozen=True)

    index_name: str = Field(..., min_length=1, description="Target OpenSearch index name")
    dimension: int = Field(..., gt=0, description="Vector dimension of the embedding model")
    shards: int = Field(default=1, gt=0, description="Number of primary shards")
    replicas: int = Field(default=1, ge=0, description="Number of replica shards")


class OpenSearchDeleteSchema(BaseModel):
    """Schema encapsulating parameters required for OpenSearch document deletion."""
    model_config = ConfigDict(frozen=True)

    index_name: str = Field(..., min_length=1, description="Target OpenSearch index name")
    doc_ids: List[str] = Field(..., min_length=1, description="List of document IDs (_id) to delete")
    routing: Optional[str] = Field(default=None, description="OpenSearch routing key")


class OpenSearchDeleteByFileSchema(BaseModel):
    """Schema encapsulating parameters required for deleting documents by file_id."""
    model_config = ConfigDict(frozen=True)

    index_name: str = Field(..., min_length=1, description="Target OpenSearch index name")
    file_ids: List[str] = Field(..., min_length=1, description="List of file_ids to delete")
    routing: Optional[str] = Field(default=None, description="OpenSearch routing key")
    project_id: Optional[str] = Field(default=None, description="Project ID for logical isolation in Pool mode")

class OpenSearchSyncSchema(BaseModel):
    """Schema encapsulating parameters required for OpenSearch bulk indexing."""
    model_config = ConfigDict(frozen=True)

    index_name: str = Field(..., min_length=1, description="Target OpenSearch index name")
    documents: List[Dict[str, Any]] = Field(..., min_length=1, description="List of documents to index")
    id_field: str = Field(default="chunk_id", description="Document field name mapped to _id")
    routing: Optional[str] = Field(default=None, description="OpenSearch routing key")


class OpenSearchSchemaFactory:
    """Factory responsible for evaluating business/plan logic and returning OpenSearch schemas."""

    @staticmethod
    def _resolve_tenant_routing(project) -> tuple[str, Optional[str], bool]:
        """Resolves tenant index_name, routing_key, and silo/pool isolation mode.

        Index naming strategy:
        - Enterprise (Silo): Dedicated index per project -> idx_silo_{project_id}_{model_slug}
        - Standard/Pro/Free (Pool): Shared index grouped by embedding model -> idx_pool_shared_{model_slug}
        """
        plan = getattr(project, "subscription_plan", "free").lower()
        project_id = str(project.id)

        # 1. Safely retrieve embedding configuration to avoid RelatedObjectDoesNotExist exception
        raw_model_name = "text_embedding_3_small"
        try:
            embedding_config = getattr(project, "embedding", None)
            if embedding_config:
                # Extract model from parameters dictionary or fallback to config name
                parameters = embedding_config.parameters or {}
                raw_model_name = parameters.get("model") or parameters.get("model_name") or embedding_config.name
        except ObjectDoesNotExist:
            pass

        clean_model_name = re.sub(r'[^a-z0-9]', '_', str(raw_model_name).lower())
        model_slug = re.sub(r'_+', '_', clean_model_name).strip('_')
        if not model_slug:
            model_slug = "default_model"

        # 3. Silo Mode: Only top-tier Enterprise plans get a dedicated index to prevent shard explosion
        if plan == "enterprise":
            return f"idx_silo_{project_id}_{model_slug}", None, True

        # 4. Pool Mode: Pro and Free plans share index pools grouped strictly by embedding model slug
        index_name = f"idx_pool_shared_{model_slug}"
        routing_key = f"proj_{project_id}"  # Route by project_id to optimize shard-level search performance

        return index_name, routing_key, False

    @classmethod
    def build_create_index_schema(
        cls,
        project,
        dimension: int = 1536,
        shards: int = 1,
        replicas: int = 1
    ) -> OpenSearchCreateIndexSchema:
        """Builds schema for creating an OpenSearch index with proper kNN mapping."""
        index_name, _, _ = cls._resolve_tenant_routing(project)

        return OpenSearchCreateIndexSchema(
            index_name=index_name,
            dimension=dimension,
            shards=shards,
            replicas=replicas
        )

    @classmethod
    def build_search_schema(
        cls,
        project,
        query_text: str,
        query_vector: List[float],
        mode: str = "question",
        top_k: int = 5
    ) -> OpenSearchSearchSchema:
        index_name, routing_key, is_silo = cls._resolve_tenant_routing(project)
        project_id = str(project.id)

        pipeline_map = {
            "question": "rrf_question_oriented",
            "concept":  "rrf_concept_oriented",
            "fact":     "rrf_fact_oriented"
        }
        pipeline = pipeline_map.get(mode, "rrf_question_oriented")

        # Construct 4-Stream Hybrid Query Body
        hybrid_queries = [
            {"multi_match": {"query": query_text, "fields": ["target_question", "concept_title^1.5", "evidence_text"]}},
            {"knn": {"question_vector": {"vector": query_vector, "k": top_k * 3}}},
            {"knn": {"concept_vector": {"vector": query_vector, "k": top_k * 3}}},
            {"knn": {"evidence_vector": {"vector": query_vector, "k": top_k * 3}}}
        ]

        query_body: Dict[str, Any] = {"size": top_k}

        # Apply logical isolation filter if running in Pool mode
        if is_silo:
            query_body["query"] = {"hybrid": {"queries": hybrid_queries}}
        else:
            query_body["query"] = {
                "bool": {
                    "must": [{"hybrid": {"queries": hybrid_queries}}],
                    "filter": [{"term": {"project_id": project_id}}]
                }
            }

        return OpenSearchSearchSchema(
            index_name=index_name,
            body=query_body,
            routing=routing_key,
            search_pipeline=pipeline
        )

    @classmethod
    def build_delete_schema(
        cls,
        project,
        doc_ids: List[str]
    ) -> OpenSearchDeleteSchema:
        """Builds schema for deleting documents by their explicit IDs."""
        index_name, routing_key, _ = cls._resolve_tenant_routing(project)

        return OpenSearchDeleteSchema(
            index_name=index_name,
            doc_ids=[str(doc_id) for doc_id in doc_ids],
            routing=routing_key
        )

    @classmethod
    def build_delete_by_file_schema(
        cls,
        project,
        file_ids: List[str]
    ) -> OpenSearchDeleteByFileSchema:
        """Builds schema for deleting documents by file_ids using query."""
        index_name, routing_key, is_silo = cls._resolve_tenant_routing(project)
        project_id = str(project.id)

        return OpenSearchDeleteByFileSchema(
            index_name=index_name,
            file_ids=[str(fid) for fid in file_ids],
            routing=routing_key,
            project_id=None if is_silo else project_id
        )

    @classmethod
    def build_sync_schema(
        cls,
        project,
        chunk_documents: List[Dict[str, Any]],
        id_field: str = "chunk_id"
    ) -> OpenSearchSyncSchema:
        index_name, routing_key, _ = cls._resolve_tenant_routing(project)

        # Inject project_id into each document to ensure tenant isolation in Pool mode
        project_id = str(project.id)
        for doc in chunk_documents:
            doc["project_id"] = project_id

        return OpenSearchSyncSchema(
            index_name=index_name,
            documents=chunk_documents,
            id_field=id_field,
            routing=routing_key
        )
