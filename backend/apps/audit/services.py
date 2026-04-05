from .models import AuditLog

REDACTED_AUDIT_VALUE = '[REDACTED]'

SENSITIVE_AUDIT_KEYS = {
    'account_number',
    'account_number_encrypted',
    'aadhaar_identifier',
    'address',
    'address_line1',
    'address_line2',
    'alternate_phone_number',
    'annual_cess',
    'annual_standard_deduction',
    'annual_tax_before_cess',
    'annual_tax_total',
    'annual_taxable_after_sd',
    'annual_taxable_gross',
    'city',
    'country',
    'employee_deductions',
    'employer_contributions',
    'gross_pay',
    'identifier',
    'ifsc',
    'ifsc_encrypted',
    'income_tax',
    'monthly_amount',
    'net_pay',
    'pan_identifier',
    'pan_number',
    'phone_emergency',
    'phone_number',
    'phone_personal',
    'pincode',
    'postal_code',
    'salary',
    'salary_structure',
    'state',
    'state_code',
    'total_deductions',
}

SENSITIVE_AUDIT_KEY_SUBSTRINGS = (
    'password',
    'secret',
    'token',
)


def _is_sensitive_audit_key(key):
    key_normalized = str(key).strip().lower()
    if key_normalized in SENSITIVE_AUDIT_KEYS:
        return True
    return any(fragment in key_normalized for fragment in SENSITIVE_AUDIT_KEY_SUBSTRINGS)


def sanitize_audit_payload(payload):
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if _is_sensitive_audit_key(key):
                sanitized[key] = REDACTED_AUDIT_VALUE
            else:
                sanitized[key] = sanitize_audit_payload(value)
        return sanitized

    if isinstance(payload, list):
        return [sanitize_audit_payload(value) for value in payload]

    if isinstance(payload, tuple):
        return [sanitize_audit_payload(value) for value in payload]

    return payload


def log_audit_event(actor, action, organisation=None, target=None, payload=None, request=None):
    payload = sanitize_audit_payload(payload or {})
    target_type = target.__class__.__name__ if target is not None else ''
    target_id = getattr(target, 'id', None) if target is not None else None
    ip_address = None
    user_agent = ''
    if request is not None:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    return AuditLog.objects.create(
        actor=actor,
        organisation=organisation,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
