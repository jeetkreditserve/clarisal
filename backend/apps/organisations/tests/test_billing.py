from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.organisations.billing.base import PaymentEvent, PaymentOrder, WebhookSignatureError
from apps.organisations.models import (
    Invoice,
    Organisation,
    OrganisationAccessState,
    OrganisationBillingProvider,
    OrganisationBillingStatus,
    OrganisationLicenceBatch,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
    Payment,
    PaymentStatus,
)
from apps.organisations.services import create_payment_order, generate_invoice, process_payment_webhook


class FakeGateway:
    gateway_name = OrganisationBillingProvider.RAZORPAY

    def create_order(self, amount, currency, receipt, notes):
        return PaymentOrder(
            gateway_order_id='order_test_123',
            amount=amount,
            currency=currency,
            gateway_options={'key': 'rzp_test_key', 'key_id': 'rzp_test_key', 'order_id': 'order_test_123'},
        )

    def verify_webhook_signature(self, payload, signature):
        return signature == 'valid-signature'

    def parse_webhook_event(self, payload):
        return PaymentEvent(
            gateway_payment_id='pay_test_123',
            gateway_order_id='order_test_123',
            status=PaymentStatus.SUCCESS,
            amount=Decimal('1180.00'),
            raw_payload=payload,
        )

    def create_subscription(self, plan_id, customer_email):
        return 'sub_test_123'


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='billing-ct@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def organisation(ct_user):
    return Organisation.objects.create(
        name='Billing Org',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
        country_code='IN',
        currency='INR',
    )


@pytest.fixture
def licence_batch(organisation):
    return OrganisationLicenceBatch.objects.create(
        organisation=organisation,
        quantity=10,
        price_per_licence_per_month=Decimal('100.00'),
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        billing_months=1,
        total_amount=Decimal('1000.00'),
    )


@pytest.mark.django_db
def test_create_payment_order_creates_pending_payment(organisation, licence_batch, monkeypatch):
    monkeypatch.setattr('apps.organisations.services.get_billing_gateway', lambda org: FakeGateway())

    response = create_payment_order(organisation, licence_batch, Decimal('1000.00'))

    payment = Payment.objects.get()
    assert payment.status == PaymentStatus.PENDING
    assert payment.gateway == OrganisationBillingProvider.RAZORPAY
    assert payment.gateway_order_id == 'order_test_123'
    assert response['gateway_options']['order_id'] == 'order_test_123'
    assert response['gateway_options']['key'] == 'rzp_test_key'
    assert response['gateway_options']['key_id'] == 'rzp_test_key'


@pytest.mark.django_db
def test_create_payment_order_reuses_existing_pending_payment(organisation, licence_batch, monkeypatch):
    monkeypatch.setattr('apps.organisations.services.get_billing_gateway', lambda org: FakeGateway())

    first = create_payment_order(organisation, licence_batch, Decimal('1000.00'))
    second = create_payment_order(organisation, licence_batch, Decimal('1000.00'))

    assert first['id'] == second['id']
    assert Payment.objects.count() == 1


@pytest.mark.django_db
def test_process_payment_webhook_marks_payment_success_and_batch_paid(organisation, licence_batch, monkeypatch):
    payment = Payment.objects.create(
        organisation=organisation,
        licence_batch=licence_batch,
        amount=Decimal('1000.00'),
        currency='INR',
        gateway=OrganisationBillingProvider.RAZORPAY,
        gateway_order_id='order_test_123',
        idempotency_key='payment:test',
    )
    delayed = {}

    monkeypatch.setattr('apps.organisations.services.get_gateway_by_name', lambda gateway_name: FakeGateway())
    monkeypatch.setattr('apps.organisations.tasks.generate_invoice_task.delay', lambda payment_id: delayed.setdefault('payment_id', payment_id))

    result = process_payment_webhook(b'{"event": "payment.captured"}', 'valid-signature', 'RAZORPAY')

    payment.refresh_from_db()
    licence_batch.refresh_from_db()
    assert result == {'status': 'processed'}
    assert payment.status == PaymentStatus.SUCCESS
    assert payment.gateway_payment_id == 'pay_test_123'
    assert licence_batch.payment_status == 'PAID'
    assert licence_batch.payment_reference == 'pay_test_123'
    assert delayed['payment_id'] == str(payment.id)


@pytest.mark.django_db
def test_process_payment_webhook_rejects_invalid_signature(organisation, licence_batch, monkeypatch):
    Payment.objects.create(
        organisation=organisation,
        licence_batch=licence_batch,
        amount=Decimal('1000.00'),
        currency='INR',
        gateway=OrganisationBillingProvider.RAZORPAY,
        gateway_order_id='order_test_123',
        idempotency_key='payment:test',
    )
    monkeypatch.setattr('apps.organisations.services.get_gateway_by_name', lambda gateway_name: FakeGateway())

    with pytest.raises(WebhookSignatureError):
        process_payment_webhook(b'{"event": "payment.captured"}', 'bad-signature', 'RAZORPAY')


@pytest.mark.django_db
def test_process_payment_webhook_is_idempotent_for_completed_payment(organisation, licence_batch, monkeypatch):
    Payment.objects.create(
        organisation=organisation,
        licence_batch=licence_batch,
        amount=Decimal('1000.00'),
        currency='INR',
        gateway=OrganisationBillingProvider.RAZORPAY,
        gateway_order_id='order_test_123',
        gateway_payment_id='pay_test_123',
        status=PaymentStatus.SUCCESS,
        completed_at=timezone.now(),
        idempotency_key='payment:test',
    )
    monkeypatch.setattr('apps.organisations.services.get_gateway_by_name', lambda gateway_name: FakeGateway())

    result = process_payment_webhook(b'{"event": "payment.captured"}', 'valid-signature', 'RAZORPAY')

    assert result == {'status': 'already_processed'}


@pytest.mark.django_db
def test_generate_invoice_uploads_pdf_and_uses_sequential_number(organisation, licence_batch, monkeypatch):
    uploads = []

    def fake_upload(file_obj, key, content_type):
        uploads.append({'key': key, 'content_type': content_type, 'payload': file_obj.read()})

    monkeypatch.setattr('apps.organisations.services._render_invoice_pdf', lambda invoice: b'%PDF-1.7 invoice')
    monkeypatch.setattr('apps.organisations.services.upload_file', fake_upload)

    first_payment = Payment.objects.create(
        organisation=organisation,
        licence_batch=licence_batch,
        amount=Decimal('1000.00'),
        currency='INR',
        gateway=OrganisationBillingProvider.RAZORPAY,
        gateway_order_id='order_test_123',
        gateway_payment_id='pay_test_123',
        status=PaymentStatus.SUCCESS,
        completed_at=timezone.now(),
        idempotency_key='payment:test:1',
    )
    second_batch = OrganisationLicenceBatch.objects.create(
        organisation=organisation,
        quantity=5,
        price_per_licence_per_month=Decimal('200.00'),
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
        billing_months=1,
        total_amount=Decimal('1000.00'),
    )
    second_payment = Payment.objects.create(
        organisation=organisation,
        licence_batch=second_batch,
        amount=Decimal('1000.00'),
        currency='INR',
        gateway=OrganisationBillingProvider.RAZORPAY,
        gateway_order_id='order_test_456',
        gateway_payment_id='pay_test_456',
        status=PaymentStatus.SUCCESS,
        completed_at=timezone.now(),
        idempotency_key='payment:test:2',
    )

    first_invoice = generate_invoice(first_payment)
    second_invoice = generate_invoice(second_payment)

    assert first_invoice.invoice_number.endswith('000001')
    assert second_invoice.invoice_number.endswith('000002')
    assert first_invoice.gst_amount == Decimal('180.00')
    assert first_invoice.total_amount == Decimal('1180.00')
    assert uploads[0]['content_type'] == 'application/pdf'
    assert Invoice.objects.count() == 2


@pytest.mark.django_db
def test_org_admin_can_create_payment_order_via_api(organisation, licence_batch, ct_user, monkeypatch):
    admin_user = User.objects.create_user(
        email='billing-admin@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=admin_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    monkeypatch.setattr('apps.organisations.services.get_billing_gateway', lambda org: FakeGateway())
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.post(
        '/api/v1/org/billing/payment-orders/',
        {'licence_batch_id': str(licence_batch.id)},
        format='json',
    )

    assert response.status_code == 201
    assert response.data['gateway'] == OrganisationBillingProvider.RAZORPAY
    assert response.data['status'] == PaymentStatus.PENDING


@pytest.mark.django_db
def test_billing_webhook_view_acknowledges_and_queues_processing(monkeypatch):
    queued = {}

    monkeypatch.setattr(
        'apps.organisations.views.process_payment_webhook_task',
        SimpleNamespace(
            delay=lambda payload, signature, gateway_name: queued.update(
                {
                    'payload': payload,
                    'signature': signature,
                    'gateway_name': gateway_name,
                }
            )
        ),
        raising=False,
    )
    monkeypatch.setattr('apps.organisations.views.get_gateway_by_name', lambda gateway_name: FakeGateway(), raising=False)

    def should_not_run_inline(*args, **kwargs):
        raise AssertionError('Webhook processing should be queued, not run inline.')

    monkeypatch.setattr('apps.organisations.views.process_payment_webhook', should_not_run_inline, raising=False)

    client = APIClient()
    response = client.post(
        '/api/v1/billing/webhooks/razorpay/',
        data=b'{"event": "payment.captured"}',
        content_type='application/json',
        HTTP_X_RAZORPAY_SIGNATURE='valid-signature',
    )

    assert response.status_code == 200
    assert response.data == {'status': 'accepted'}
    assert queued == {
        'payload': '{"event": "payment.captured"}',
        'signature': 'valid-signature',
        'gateway_name': 'RAZORPAY',
    }


@pytest.mark.django_db
def test_billing_webhook_view_rejects_invalid_signature_without_queueing(monkeypatch):
    queued = {'called': False}

    monkeypatch.setattr(
        'apps.organisations.views.process_payment_webhook_task',
        SimpleNamespace(delay=lambda *args, **kwargs: queued.__setitem__('called', True)),
        raising=False,
    )
    monkeypatch.setattr('apps.organisations.views.get_gateway_by_name', lambda gateway_name: FakeGateway(), raising=False)

    client = APIClient()
    response = client.post(
        '/api/v1/billing/webhooks/razorpay/',
        data=b'{"event": "payment.captured"}',
        content_type='application/json',
        HTTP_X_RAZORPAY_SIGNATURE='bad-signature',
    )

    assert response.status_code == 400
    assert queued['called'] is False
