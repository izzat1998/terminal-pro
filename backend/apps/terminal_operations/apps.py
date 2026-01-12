from django.apps import AppConfig


class TerminalOperationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.terminal_operations"

    def ready(self):
        """Import signals when app is ready to register signal handlers."""
        import apps.terminal_operations.signals  # noqa: F401
