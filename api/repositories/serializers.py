from rest_framework import serializers
from repositories.models import RepositoryFile, ChunkData, SupportedFileType, ProcessStatus
from repositories.constants import ImpactLevel
from adrf.serializers import ModelSerializer, Serializer


# ======================================================================
# Nested Serializers for Layer 1: Alignment & Scope
# ======================================================================

class ChunkScopeSerializer(Serializer):
    """
    Scope and boundary limits for strategy alignment.
    Mapped to `ChunkScope` TypeScript interface.
    """
    domain = serializers.CharField(
        help_text='Target business/technical domain (e.g., "IT Architecture & Compliance")'
    )
    impactLevel = serializers.ChoiceField(
        choices=ImpactLevel.choices,
        help_text="Level of impact on decision-making ('strategic' | 'tactical' | 'operational')"
    )
    boundaries = serializers.ListField(
        child=serializers.CharField(),
        default=list,
        help_text='Non-negotiable rules or hard constraints'
    )


class ChunkAlignmentSerializer(Serializer):
    """
    Layer 1: Contextual questions and non-negotiable boundaries for driving discussions.
    Mapped to `ChunkAlignment` TypeScript interface.
    """
    targetQuestion = serializers.CharField(
        help_text="Core decision dilemma or question triggered by this chunk"
    )
    scope = ChunkScopeSerializer(
        help_text="Boundary parameters and impact domain"
    )


# ======================================================================
# Nested Serializers for Layer 2: Abstraction Layer
# ======================================================================

class ChunkConceptSerializer(Serializer):
    """
    Layer 2: High-level concepts and structural propositions (does NOT duplicate text details).
    Mapped to `ChunkConcept` TypeScript interface.
    """
    title = serializers.CharField(
        help_text='High-level proposition or rule title (e.g., "Data Sovereignty vs. Architectural Agility")'
    )
    description = serializers.CharField(
        help_text="Contextual description explaining real-world impact and constraint mechanisms"
    )


# ======================================================================
# 3. Nested Serializers for Layer 3: Token & Entity-Relation Layer
# ======================================================================

class TripleItemSerializer(Serializer):
    """
    Expresses a bound semantic triple: Entity -> Relation -> Metric/Constraint.
    Mapped to `TripleItem` TypeScript interface.
    """
    subject = serializers.CharField(help_text="Subject entity")
    predicate = serializers.CharField(help_text="Predicate/Operator relation")
    object = serializers.CharField(help_text="Object/Metric constraint")


class ChunkKeywordsSerializer(Serializer):
    """
    Layer 3: Captures bound entity-metric pairs and general domain tags to prevent association mismatch.
    Mapped to `ChunkKeywords` TypeScript interface.
    """
    triples = TripleItemSerializer(
        many=True,
        default=list,
        help_text="List of bound semantic triples ensuring strict relationship coupling"
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        default=list,
        help_text='General high-level domain or thematic tags (e.g., ["finance", "compliance"])'
    )


# ======================================================================
# Nested Serializers for Layer 4: Fact & Evidence Layer
# ======================================================================

class ChunkEvidenceSerializer(Serializer):
    """
    Layer 4: Raw text snippets and location pointers for grounding and auditability.
    Mapped to `ChunkEvidence` TypeScript interface.
    """
    excerptText = serializers.CharField(
        help_text="Exact verbatim excerpt from the document (100–300 words)"
    )
    location = serializers.CharField(
        help_text='Location pointer within the source document (e.g., "Page 5, Section 3.2")'
    )


# ======================================================================
# Main Entity Serializers
# ======================================================================

class ChunkDataSerializer(ModelSerializer):
    """
    Unified Repository Chunk Entity Serializer.
    Validates and maps nested JSON structures into JSONFields.
    Mapped to `ChunkData` TypeScript interface.
    """
    alignment = ChunkAlignmentSerializer(
        help_text="Layer 1: Alignment & Scope"
    )
    concept = ChunkConceptSerializer(
        help_text="Layer 2: Abstract Concept"
    )
    keywords = ChunkKeywordsSerializer(
        help_text="Layer 3: Keyword Tokens & Triples"
    )
    evidence = ChunkEvidenceSerializer(
        help_text="Layer 4: Raw Fact & Evidence"
    )

    class Meta:
        model = ChunkData
        fields = [
            'id',
            'file',
            'alignment',
            'concept',
            'keywords',
            'evidence',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RepositoryFileSerializer(ModelSerializer):
    """
    Repository Document Entity Serializer.
    Mapped to `RepositoryFile` TypeScript interface.
    """
    fileName = serializers.CharField(source='file_name')
    fileSize = serializers.CharField(source='file_size')
    fileType = serializers.ChoiceField(choices=SupportedFileType.choices, source='file_type')
    chunkCount = serializers.IntegerField(source='chunk_count', read_only=True)
    status = serializers.ChoiceField(choices=ProcessStatus.choices, required=False)
    createdAt = serializers.DateTimeField(
        source='created_at',
        read_only=True,
        help_text="The timestamp when the project was created"
    )
    updatedAt = serializers.DateTimeField(
        source='updated_at',
        read_only=True,
        help_text="The timestamp when the project was last updated"
    )
    chunks = ChunkDataSerializer(many=True, read_only=True)

    class Meta:
        model = RepositoryFile
        fields = [
            'id',
            'fileName',
            'fileSize',
            'fileType',
            'chunkCount',
            'status',
            'createdAt',
            'updatedAt',
            'chunks',
        ]
        read_only_fields = ['id', 'chunkCount', 'chunks', 'createdAt', 'updatedAt']
