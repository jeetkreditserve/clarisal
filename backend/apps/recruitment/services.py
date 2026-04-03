from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    Application,
    ApplicationStage,
    Candidate,
    JobPosting,
    JobPostingStatus,
    OfferLetter,
    OfferStatus,
)

TERMINAL_STAGES = {ApplicationStage.HIRED, ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN}


def create_job_posting(organisation, title: str, description: str = '', actor=None, **kwargs) -> JobPosting:
    return JobPosting.objects.create(
        organisation=organisation,
        title=title,
        description=description,
        status=JobPostingStatus.DRAFT,
        created_by=actor,
        modified_by=actor,
        **kwargs,
    )


def publish_job_posting(posting: JobPosting, actor=None) -> JobPosting:
    posting.status = JobPostingStatus.OPEN
    posting.posted_at = timezone.now()
    posting.modified_by = actor
    posting.save(update_fields=['status', 'posted_at', 'modified_at', 'modified_by'])
    return posting


def add_candidate(organisation, first_name: str, last_name: str, email: str, actor=None, **kwargs) -> Candidate:
    candidate, _ = Candidate.objects.get_or_create(
        organisation=organisation,
        email=email,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'created_by': actor,
            'modified_by': actor,
            **kwargs,
        },
    )
    return candidate


def apply_to_posting(candidate: Candidate, posting: JobPosting, actor=None) -> Application:
    application, created = Application.objects.get_or_create(
        candidate=candidate,
        job_posting=posting,
        defaults={
            'stage': ApplicationStage.APPLIED,
            'created_by': actor,
            'modified_by': actor,
        },
    )
    if not created:
        raise ValueError('Candidate has already applied to this posting.')
    return application


def advance_application_stage(application: Application, new_stage: str, actor=None) -> Application:
    if application.stage in TERMINAL_STAGES:
        raise ValueError(f'Cannot advance a {application.stage} application.')
    application.stage = new_stage
    application.modified_by = actor
    application.save(update_fields=['stage', 'modified_at', 'modified_by'])
    return application


def create_offer_letter(
    application: Application,
    ctc_annual: Decimal,
    joining_date: date | None = None,
    template_text: str = '',
    expires_at=None,
    actor=None,
) -> OfferLetter:
    return OfferLetter.objects.create(
        application=application,
        ctc_annual=ctc_annual,
        joining_date=joining_date,
        status=OfferStatus.DRAFT,
        template_text=template_text,
        expires_at=expires_at,
        created_by=actor,
        modified_by=actor,
    )


def accept_offer_and_onboard(offer: OfferLetter, actor=None):
    from apps.employees.services import create_employee_from_offer

    if offer.status == OfferStatus.ACCEPTED and offer.onboarded_employee_id:
        return offer.onboarded_employee
    if offer.status not in {OfferStatus.DRAFT, OfferStatus.SENT, OfferStatus.ACCEPTED}:
        raise ValueError('Only draft or sent offers can be accepted.')

    with transaction.atomic():
        offer.status = OfferStatus.ACCEPTED
        offer.accepted_at = timezone.now()
        offer.modified_by = actor
        offer.save(update_fields=['status', 'accepted_at', 'modified_at', 'modified_by'])

        advance_application_stage(offer.application, ApplicationStage.HIRED, actor=actor)
        employee = create_employee_from_offer(offer, actor=actor)
        offer.onboarded_employee = employee
        offer.save(update_fields=['onboarded_employee', 'modified_at'])

    return employee
