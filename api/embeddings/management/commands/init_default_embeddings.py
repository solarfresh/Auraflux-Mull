from django.core.management.base import BaseCommand
from django.db import transaction
from embeddings.models import DefaultEmbeddingConfig

DEFAULT_EMBEDDING_CONFIGS = [
    {
        "role": "SearchEmbedding",
        "name": "Search Embedding",
    },
]


class Command(BaseCommand):
    help = "Initializes or updates DefaultEmbeddingConfig entries for system embeddings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            type=str,
            help="Specify a single embedding role to update (e.g., --role 'default_search').",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        target_role = options.get("role")
        configs_to_process = DEFAULT_EMBEDDING_CONFIGS

        if target_role:
            configs_to_process = [cfg for cfg in DEFAULT_EMBEDDING_CONFIGS if cfg["role"] == target_role]
            if not configs_to_process:
                self.stdout.write(self.style.ERROR(f"Role '{target_role}' not found in default configuration."))
                return

        created_count = 0
        updated_count = 0

        for config_data in configs_to_process:
            role_name = config_data["role"]
            config_obj, created = DefaultEmbeddingConfig.objects.update_or_create(
                role=role_name,
                defaults={
                    "name": config_data["name"],
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"[CREATED] Role: '{role_name}' ({config_data['name']})"))
            else:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"[UPDATED] Role: '{role_name}' ({config_data['name']})"))

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\nExecution finished. Created: {created_count}, Updated: {updated_count}"
            )
        )