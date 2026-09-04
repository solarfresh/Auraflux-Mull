from django.apps import AppConfig


class RepositoriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repositories'
    label = 'repositories'

    def ready(self):
        import sys

        is_web_server = any(
            server in arg
            for arg in sys.argv
            for server in ['runserver', 'gunicorn', 'uvicorn']
        )

        if is_web_server:
            from .utils import setup_opensearch
            setup_opensearch()
