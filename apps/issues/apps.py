# apps/issues/apps.py
from django.apps import AppConfig

class IssuesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.issues'

    def ready(self):
        import importlib
        importlib.import_module('apps.issues.signals')  # Ensure signals.py exists