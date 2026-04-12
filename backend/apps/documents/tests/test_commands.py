from io import StringIO

import pytest
from django.core.management import call_command

from apps.documents.models import OnboardingDocumentType
from apps.documents.services import DEFAULT_ONBOARDING_DOCUMENT_TYPES


@pytest.mark.django_db
def test_seed_document_types_command_is_idempotent():
    stdout = StringIO()

    call_command('seed_document_types', stdout=stdout)
    call_command('seed_document_types', stdout=stdout)

    assert OnboardingDocumentType.objects.count() == len(DEFAULT_ONBOARDING_DOCUMENT_TYPES)
    assert 'Seeded' in stdout.getvalue()
