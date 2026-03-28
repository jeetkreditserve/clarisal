from django.apps import AppConfig


class LocationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.locations'
    label = 'locations'

    def ready(self):
        import apps.locations.signals  # noqa
