import json
import logging
from email.utils import parseaddr
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when the configured transactional email provider rejects a message."""


def _parse_sender():
    configured = getattr(settings, 'ZEPTOMAIL_FROM_EMAIL', '') or getattr(settings, 'DEFAULT_FROM_EMAIL', '')
    display_name = getattr(settings, 'ZEPTOMAIL_FROM_NAME', '')
    parsed_name, parsed_email = parseaddr(configured)
    return {
        'address': parsed_email or configured,
        'name': display_name or parsed_name or 'Clarisal',
    }


def _zeptomail_is_configured():
    return bool(
        getattr(settings, 'ZEPTOMAIL_API_URL', '')
        and getattr(settings, 'ZEPTOMAIL_API_KEY', '')
    )


def _send_via_zeptomail(*, subject, recipient_email, text_body, html_body=''):
    sender = _parse_sender()
    payload = {
        'from': {
            'address': sender['address'],
            'name': sender['name'],
        },
        'to': [
            {
                'email_address': {
                    'address': recipient_email,
                }
            }
        ],
        'subject': subject,
        'textbody': text_body,
        'htmlbody': html_body or f'<pre>{text_body}</pre>',
    }
    body = json.dumps(payload).encode('utf-8')
    req = urllib_request.Request(
        getattr(settings, 'ZEPTOMAIL_API_URL'),
        data=body,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Zoho-enczapikey {getattr(settings, "ZEPTOMAIL_API_KEY")}',
        },
        method='POST',
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            status = getattr(response, 'status', response.getcode())
            if status >= 400:
                raise EmailDeliveryError(f'ZeptoMail returned HTTP {status}.')
    except urllib_error.HTTPError as exc:
        details = exc.read().decode('utf-8', errors='ignore')
        logger.warning('ZeptoMail HTTP error: %s %s', exc.code, details)
        raise EmailDeliveryError(f'ZeptoMail returned HTTP {exc.code}.') from exc
    except urllib_error.URLError as exc:
        logger.warning('ZeptoMail connection error: %s', exc)
        raise EmailDeliveryError('Unable to reach ZeptoMail.') from exc


def _send_via_django_email_backend(*, subject, recipient_email, text_body, html_body=''):
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
        to=[recipient_email],
    )
    if html_body:
        message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)


def send_transactional_email(*, subject, recipient_email, text_body, html_body=''):
    if _zeptomail_is_configured():
        _send_via_zeptomail(
            subject=subject,
            recipient_email=recipient_email,
            text_body=text_body,
            html_body=html_body,
        )
        return

    logger.info('ZeptoMail config missing; falling back to Django email backend for %s', recipient_email)
    _send_via_django_email_backend(
        subject=subject,
        recipient_email=recipient_email,
        text_body=text_body,
        html_body=html_body,
    )
