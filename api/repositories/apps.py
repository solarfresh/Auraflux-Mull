from django.apps import AppConfig

from .utils import setup_opensearch


class RepositoriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repositories'
    label = 'repositories'

    def ready(self):
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv or 'uvicorn' in sys.argv:
            setup_opensearch()
