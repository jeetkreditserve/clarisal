from __future__ import annotations

from dataclasses import dataclass

from apps.organisations.country_metadata import normalize_phone_number

from .models import ContactKind, EmailAddress, Person, PhoneNumber


def normalize_email_address(value: str) -> str:
    return (value or '').strip().lower()


@dataclass
class ResolvedContacts:
    person: Person
    email_address: EmailAddress | None
    phone_number: PhoneNumber | None
    normalized_email: str
    normalized_phone: str


def _ensure_primary_email(person: Person, email_record: EmailAddress):
    person.email_addresses.exclude(id=email_record.id).filter(is_primary=True).update(is_primary=False)
    if not email_record.is_primary or not email_record.is_login:
        email_record.is_primary = True
        email_record.is_login = True
        email_record.save(update_fields=['is_primary', 'is_login', 'updated_at'])


def _ensure_primary_phone(person: Person, phone_record: PhoneNumber):
    person.phone_numbers.exclude(id=phone_record.id).filter(is_primary=True).update(is_primary=False)
    if not phone_record.is_primary:
        phone_record.is_primary = True
        phone_record.save(update_fields=['is_primary', 'updated_at'])


def resolve_person_contacts(
    *,
    email: str = '',
    phone: str = '',
    person: Person | None = None,
    email_kind: str = ContactKind.WORK,
    phone_kind: str = ContactKind.WORK,
) -> ResolvedContacts:
    normalized_email = normalize_email_address(email)
    normalized_phone = normalize_phone_number(phone) if phone else ''

    email_record = None
    phone_record = None

    if normalized_email:
        email_record = EmailAddress.objects.select_related('person').filter(normalized_email=normalized_email).first()
    if normalized_phone:
        phone_record = PhoneNumber.objects.select_related('person').filter(e164_number=normalized_phone).first()

    resolved_person = person
    if email_record and phone_record and email_record.person_id != phone_record.person_id:
        raise ValueError('This email and phone number already belong to different people.')
    if resolved_person and email_record and email_record.person_id != resolved_person.id:
        raise ValueError('This email address is already assigned to another person.')
    if resolved_person and phone_record and phone_record.person_id != resolved_person.id:
        raise ValueError('This phone number is already assigned to another person.')

    if resolved_person is None:
        resolved_person = email_record.person if email_record else None
    if resolved_person is None:
        resolved_person = phone_record.person if phone_record else None
    if resolved_person is None:
        resolved_person = Person.objects.create()

    if normalized_email:
        if email_record is None:
            resolved_person.email_addresses.filter(is_primary=True).update(is_primary=False)
            email_record = EmailAddress.objects.create(
                person=resolved_person,
                email=normalized_email,
                normalized_email=normalized_email,
                kind=email_kind,
                is_primary=True,
                is_login=True,
            )
        else:
            changed = False
            if email_record.person_id != resolved_person.id:
                raise ValueError('This email address is already assigned to another person.')
            if email_record.email != normalized_email:
                email_record.email = normalized_email
                changed = True
            if email_record.kind != email_kind:
                email_record.kind = email_kind
                changed = True
            if changed:
                email_record.save(update_fields=['email', 'kind', 'updated_at'])
        _ensure_primary_email(resolved_person, email_record)

    if normalized_phone:
        if phone_record is None:
            resolved_person.phone_numbers.filter(is_primary=True).update(is_primary=False)
            phone_record = PhoneNumber.objects.create(
                person=resolved_person,
                e164_number=normalized_phone,
                display_number=phone,
                kind=phone_kind,
                is_primary=True,
            )
        else:
            changed = False
            if phone_record.person_id != resolved_person.id:
                raise ValueError('This phone number is already assigned to another person.')
            if phone_record.display_number != phone:
                phone_record.display_number = phone
                changed = True
            if phone_record.kind != phone_kind:
                phone_record.kind = phone_kind
                changed = True
            if changed:
                phone_record.save(update_fields=['display_number', 'kind', 'updated_at'])
        _ensure_primary_phone(resolved_person, phone_record)

    return ResolvedContacts(
        person=resolved_person,
        email_address=email_record,
        phone_number=phone_record,
        normalized_email=normalized_email,
        normalized_phone=normalized_phone,
    )


def ensure_user_contact_identity(user):
    normalized_email = normalize_email_address(user.email)
    if not normalized_email:
        raise ValueError('Email is required.')
    resolved = resolve_person_contacts(
        email=normalized_email,
        person=user.person,
        email_kind=ContactKind.WORK,
    )
    user.email = resolved.normalized_email
    user.person = resolved.person
    return user
