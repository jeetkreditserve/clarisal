from django.apps import AppConfig


class DepartmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.departments'
    label = 'departments'

    def ready(self):
        import apps.departments.signals  # noqa
