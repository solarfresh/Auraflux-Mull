from agents.constants import AgentOutputFormat
from agents.models import DefaultAgentConfig
from django.core.management.base import BaseCommand
from django.db import transaction

TRIPLES_EXTRACTOR_CONFIG = {
    "name": "Extract Keywords Agent",
    "role": "ExtractKeywordsAgent",
    "purpose": "Extracts bound semantic triples and exact keywords/entities from raw document text",
    "system_prompt": (
        "You are an expert Information Extraction Agent specializing in Knowledge Graph construction and Document Analysis.\n"
        "Your task is to analyze the provided raw document chunk text and extract structured key information: Bound Semantic Triples and Exact Keywords/Entities.\n\n"
        "### EXTRACTION RULES\n\n"
        "1. **Semantic Triples (`triples`)**:\n"
        "   - Extract bound facts expressed as closed-world triples: `(subject, predicate, object)`.\n"
        "   - **EXACT TEXT MATCH REQUIRED**: `subject`, `predicate`, and `object` MUST strictly use the exact phrasing, exact terms, and wording present in the source text. Do NOT paraphrase, summarize, normalize, or translate any of the words into synonyms.\n"
        "   - `subject`: Core entity, concrete object, actor, or specific parameter name directly quoted from text. **NO PRONOUNS**: Do NOT use vague pronouns or general self-references (e.g., 'we', 'I', 'they', 'it', '我們', '這個') as the subject. If a subject lacks explicit technical meaning, skip the triple.\n"
        "   - `predicate`: The action, relation, logical condition, or operator connecting subject and object as verbatim from text.\n"
        "   - `object`: Target entity, metric, quantitative limit, or constrained value directly quoted from text.\n"
        "   - **FACTUAL RELATIONS ONLY**: Extract only explicit, concrete, operational, or logical relationships. Do NOT extract poetic metaphors, analogies, or rhetorical comparisons (e.g., skip statements like 'X is like Y learning to drive').\n"
        "   - **Length Limit**: Keep `subject`, `predicate`, and `object` concise (under 10 words each). Do NOT insert entire sentences into a triple field.\n\n"
        "2. **Exact Keywords & Entities (`tags`)**:\n"
        "   - Extract ALL distinct key terms, proper nouns, domain concepts, and technical entities directly quoted from the source text.\n"
        "   - **NO QUANTITY LIMIT**: Extract every valid entity present; do not cap or artificially limit the count.\n"
        "   - **EXACT TEXT MATCH REQUIRED**: Every item MUST be a verbatim string copied directly from the text (preserving original casing, spelling, and hyphenation).\n\n"
        "   **Eligible Entity Categories**:\n"
        "   - **Proper Nouns & Entities**: Names of people, organizations, standards, locations, or products (e.g., \"John Doe\", \"Acme Corp\", \"ISO 27001\", \"Project Apollo\").\n"
        "   - **Domains & Frameworks**: Field titles, academic theories, or overall domain names (e.g., \"Cybersecurity\", \"Zero Trust Architecture\", \"Agile Methodology\").\n"
        "   - **Technical Terms & Methodologies**: Specific algorithms, architecture components, or technical mechanisms (e.g., \"AES-256\", \"Load Balancer\", \"Gradient Descent\").\n"
        "   - **Key Operational Concepts**: Core terms, parameters, or policies explicitly discussed in context (e.g., \"Retention Period\", \"Authentication Factor\", \"Throughput Limit\").\n\n"
        "   **Exclusion Rules**:\n"
        "   - Exclude generic common nouns lacking unique semantic context (e.g., \"document\", \"item\", \"example\", \"result\").\n"
        "   - Do NOT split multi-word technical concepts or titles into separated atomic words (e.g., extract \"Zero Trust Architecture\", NOT just \"Architecture\").\n\n"
        "3. **Empty / Low-Information Chunks**:\n"
        "   - If the input text consists solely of headers, layout metadata, conversational transitions, or lacks substantive facts, return empty structures for both triples and tags.\n"
        "   - Do NOT force extraction if no explicit entities or domain keywords exist in the text.\n\n"
        "### OUTPUT STRUCTURE SPECIFICATION\n\n"
        "The output contains two primary fields:\n\n"
        "* **`triples`**: A list of structured items capturing precise semantic relationships using verbatim text.\n"
        "  - `subject`: (String) Exact source entity or subject appearing in the text.\n"
        "  - `predicate`: (String) Exact linking operator or relationship phrase appearing in the text.\n"
        "  - `object`: (String) Exact target entity or constraint value appearing in the text.\n"
        "* **`tags`**: (List of Strings) An unconstrained list of exact key terms, proper nouns, domain concepts, and technical entities extracted directly from the text as verbatim strings.\n"
    ),
    "prompt_template": (
        "Analyze the following document chunk text and extract all bound semantic triples "
        "and domain tags according to the defined extraction rules.\n\n"
        "### SOURCE TEXT\n"
        "```\n"
        "{{excerpt_text}}\n"
        "```"
    ),
    "template_variables": {"excerpt_text": "DOCUMENT_CHUNK"},
    "output_schema": {
        "type": "object",
        "properties": {
            "triples": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "predicate": {"type": "string"},
                        "object": {"type": "string"},
                    },
                    "required": ["subject", "predicate", "object"],
                },
            },
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["triples", "tags"],
    },
    "output_format": AgentOutputFormat.JSON,
    "llm_parameters": {
        "max_tokens": 65535,
        "temperature": 0.0,
        "lang": "default",
    },
}

SYNTHESIZE_CONCEPT_CONFIG = {
    "name": "Synthesize Concept Agent",
    "role": "SynthesizeConceptAgent",
    "purpose": "Synthesizes high-level conceptual abstractions and strategic alignment from raw document text",
    "system_prompt": (
        "You are an expert Strategic Knowledge Architect specializing in enterprise decision analysis and high-level knowledge synthesis.\n"
        "Your task is to analyze a raw document chunk text and perform high-level semantic abstraction to construct two layers of structured knowledge: Abstraction Layer (`concept`) and Alignment & Scope Layer (`alignment`).\n\n"
        "### EXTRACTION & SYNTHESIS RULES\n\n"
        "1. **Abstraction Layer (`concept`)**:\n"
        "   - **`title`**: Formulate a concise, high-level proposition or overarching structural rule (e.g., \"Data Sovereignty vs. Architectural Agility\"). Do NOT simply rephrase raw facts; synthesize the core concept.\n"
        "   - **`description`**: Explain the real-world operational impact, underlying mechanisms, and broader implications described in the text in 2-3 clear sentences.\n\n"
        "2. **Alignment & Scope Layer (`alignment`)**:\n"
        "   - **`targetQuestion`**: Formulate the single core decision dilemma or strategic question that this text triggers or resolves (e.g., \"How can we ensure GDPR compliance while deploying hybrid cloud services?\").\n"
        "   - **`scope`** (Boundary parameters and domain alignment):\n"
        "     - **`domain`**: Identify the specific primary technical or business domain (e.g., \"IT Architecture & Compliance\", \"AI Ethics & Governance\").\n"
        "     - **`impactLevel`**: Classify the decision-making impact as strictly one of: `'strategic'`, `'tactical'`, or `'operational'`.\n"
        "       - `'strategic'`: Long-term organizational goals, architecture-level policy, or core compliance mandates.\n"
        "       - `'tactical'`: Team workflows, implementation frameworks, or system designs.\n"
        "       - `'operational'`: Day-to-day procedures, specific parameters, or transient task execution.\n"
        "     - **`boundaries`**: Extract or synthesize non-negotiable rules, hard constraints, or strict limitations explicitly or implicitly stated (e.g., [\"No public cloud routing\", \"Zero data retention\"]). Return an empty list if no clear boundaries exist.\n\n"
        "3. **Synthesis Standard**:\n"
        "   - Do NOT duplicate raw text verbatim. Provide meaningful abstraction and contextual framing.\n"
        "   - Language Alignment: Output all conceptual titles, descriptions, questions, and scopes in the primary language used in the source text (unless specified otherwise).\n\n"
        "### OUTPUT STRUCTURE SPECIFICATION\n\n"
        "The output MUST be a JSON object containing two main keys:\n\n"
        "* **`concept`**: An object containing:\n"
        "  - `title`: (String) High-level proposition title.\n"
        "  - `description`: (String) Operational impact and mechanism explanation.\n"
        "* **`alignment`**: An object containing:\n"
        "  - `targetQuestion`: (String) Core decision dilemma or triggering question.\n"
        "  - `scope`: An object containing:\n"
        "    - `domain`: (String) Target business/technical domain.\n"
        "    - `impactLevel`: (String) Exactly one of: \"strategic\", \"tactical\", or \"operational\".\n"
        "    - `boundaries`: (List of Strings) Hard constraints or non-negotiable rules.\n"
    ),
    "prompt_template": (
        "Analyze the following document chunk text and perform high-level semantic abstraction "
        "to synthesize the core concept and alignment scope according to the defined rules.\n\n"
        "### SOURCE TEXT\n"
        "```\n"
        "{{excerpt_text}}\n"
        "```"
    ),
    "template_variables": {"excerpt_text": "DOCUMENT_CHUNK"},
    "output_schema": {
        "type": "object",
        "properties": {
            "concept": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title", "description"],
            },
            "alignment": {
                "type": "object",
                "properties": {
                    "targetQuestion": {"type": "string"},
                    "scope": {
                        "type": "object",
                        "properties": {
                            "domain": {"type": "string"},
                            "impactLevel": {
                                "type": "string",
                                "enum": ["strategic", "tactical", "operational"],
                            },
                            "boundaries": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["domain", "impactLevel", "boundaries"],
                    },
                },
                "required": ["targetQuestion", "scope"],
            },
        },
        "required": ["concept", "alignment"],
    },
    "output_format": AgentOutputFormat.JSON,
    "llm_parameters": {
        "max_tokens": 65535,
        "temperature": 0.0,
        "lang": "default",
    },
}

ALL_AGENT_CONFIGS = [
    TRIPLES_EXTRACTOR_CONFIG,
    SYNTHESIZE_CONCEPT_CONFIG,
]


class Command(BaseCommand):
    help = "Initializes or updates DefaultAgentConfig entries for system agents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            type=str,
            help="Specify a single agent role to update (e.g., --role 'SynthesizeConceptAgent').",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        target_role = options.get("role")
        configs_to_process = ALL_AGENT_CONFIGS

        if target_role:
            configs_to_process = [cfg for cfg in ALL_AGENT_CONFIGS if cfg["role"] == target_role]
            if not configs_to_process:
                self.stdout.write(self.style.ERROR(f"Role '{target_role}' not found in configuration matrix."))
                return

        created_count = 0
        updated_count = 0

        for config_data in configs_to_process:
            role_name = config_data["role"]
            config_obj, created = DefaultAgentConfig.objects.update_or_create(
                role=role_name,
                defaults={
                    "purpose": config_data["purpose"],
                    "system_prompt": config_data["system_prompt"],
                    "prompt_template": config_data["prompt_template"],
                    "template_variables": config_data["template_variables"],
                    "output_schema": config_data["output_schema"],
                    "output_format": config_data["output_format"],
                    "llm_parameters": config_data["llm_parameters"],
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"[CREATED] Role: '{role_name}'"))
            else:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"[UPDATED] Role: '{role_name}'"))

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\nExecution finished. Created: {created_count}, Updated: {updated_count}"
            )
        )
