from __future__ import annotations

from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.documents.models import OnboardingDocumentType
from apps.documents.services import DOCUMENT_TYPES_SEEDED_CACHE_KEY, ensure_default_document_types


class Command(BaseCommand):
    help = 'Seed repeatable onboarding document types.'

    def handle(self, *args, **options):
        ensure_default_document_types()
        cache.set(DOCUMENT_TYPES_SEEDED_CACHE_KEY, True, timeout=3600)
        self.stdout.write(
            self.style.SUCCESS(f'Seeded {OnboardingDocumentType.objects.count()} onboarding document types.')
        )
