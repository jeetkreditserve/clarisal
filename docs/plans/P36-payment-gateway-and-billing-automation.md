# P36 — Payment Gateway & Billing Automation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate a payment gateway (Razorpay for Indian clients, Stripe for international) to automate licence payment confirmation. The licence ledger and webhook abstraction layer already exist — this plan wires them to real payment events, adds invoice PDF generation, and builds the billing management UI for org admins and CT users.

**Architecture:** The `organisations` app has a `Licence` model and a `BillingWebhook` abstraction. This plan adds: (1) Razorpay/Stripe SDK integration for order creation and webhook signature verification, (2) idempotent payment event processing, (3) invoice generation via WeasyPrint, and (4) billing management pages in the CT and org-admin portals.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · Celery · Redis · WeasyPrint · Razorpay SDK · Stripe SDK · React 19 · TypeScript · Radix UI · TanStack Query · pytest

---

## Audit Findings Addressed

- Billing/subscription: licence ledger + webhook abstraction present; no payment gateway integration; licence lifecycle is entirely manual (Gap #24 — High)
- Control Tower benchmark gap: Billing/subscription shows "Licence ledger (no gateway)" vs Zoho/Darwinbox "Full gateway" (§8.1)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/requirements.txt` | Modify | Add `razorpay` and `stripe` packages |
| `backend/apps/organisations/models.py` | Modify | Add `Payment`, `Invoice` models; add `gateway_subscription_id` to `Licence` |
| `backend/apps/organisations/migrations/XXXX_billing_payment_invoice.py` | Create | Migration for Payment and Invoice models |
| `backend/apps/organisations/services.py` | Modify | Add `create_payment_order`, `process_payment_webhook`, `generate_invoice` |
| `backend/apps/organisations/billing/razorpay.py` | Create | Razorpay SDK wrapper |
| `backend/apps/organisations/billing/stripe.py` | Create | Stripe SDK wrapper |
| `backend/apps/organisations/billing/base.py` | Create | Abstract gateway interface |
| `backend/apps/organisations/views.py` | Modify | Payment order, webhook, invoice download endpoints |
| `backend/apps/organisations/urls.py` | Modify | Register billing endpoints |
| `backend/apps/organisations/tasks.py` | Modify | Add payment failure retry task, invoice Celery task |
| `backend/apps/organisations/tests/test_billing.py` | Create | Payment flow, webhook idempotency, invoice generation tests |
| `backend/clarisal/settings/base.py` | Modify | Add `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` settings |
| `frontend/src/pages/org/BillingPage.tsx` | Create | Org admin billing and subscription management |
| `frontend/src/pages/ct/CtBillingPage.tsx` | Create | CT billing overview across all orgs |
| `frontend/src/lib/api/billing.ts` | Create | Billing API client |

---

## Task 1: Define Gateway Abstraction Layer

- [x] Create `backend/apps/organisations/billing/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class PaymentOrder:
    gateway_order_id: str
    amount: Decimal
    currency: str
    gateway_options: dict  # gateway-specific options (Razorpay: key_id; Stripe: client_secret)

@dataclass
class PaymentEvent:
    gateway_payment_id: str
    gateway_order_id: str
    status: str  # 'SUCCESS' | 'FAILED' | 'REFUNDED'
    amount: Decimal
    raw_payload: dict

class BillingGateway(ABC):
    @abstractmethod
    def create_order(self, amount: Decimal, currency: str, receipt: str, notes: dict) -> PaymentOrder:
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        pass

    @abstractmethod
    def parse_webhook_event(self, payload: dict) -> PaymentEvent:
        pass

    @abstractmethod
    def create_subscription(self, plan_id: str, customer_email: str) -> str:
        pass
```

- [x] Create `billing/razorpay.py` implementing `BillingGateway` using the `razorpay` SDK.
- [x] Create `billing/stripe.py` implementing `BillingGateway` using the `stripe` SDK.
- [x] Add a factory function `get_billing_gateway(org: Organisation) -> BillingGateway` that returns the appropriate gateway based on `org.country_code` (`IN` → Razorpay, other → Stripe) or an org-level `billing_gateway` setting.

## Task 2: Payment and Invoice Models

- [x] In `organisations/models.py`, add:

```python
class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='payments')
    licence = models.ForeignKey('Licence', on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    gateway = models.CharField(max_length=20)  # 'razorpay' | 'stripe'
    gateway_order_id = models.CharField(max_length=200, unique=True)
    gateway_payment_id = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    idempotency_key = models.CharField(max_length=100, unique=True)  # prevents duplicate processing
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

class Invoice(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='invoices')
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20)  # DRAFT | ISSUED | PAID | VOID
    storage_key = models.CharField(max_length=500, blank=True)  # S3 key for PDF
    created_at = models.DateTimeField(auto_now_add=True)
```

- [x] Add `gateway_subscription_id = models.CharField(max_length=200, null=True, blank=True)` to the `Licence` model.
- [x] Create the migration.

## Task 3: Payment Services

- [x] In `organisations/services.py`, add `create_payment_order`:

```python
def create_payment_order(
    organisation: Organisation,
    licence: Licence,
    amount: Decimal,
) -> dict:
    """
    Create a gateway payment order. Returns options to pass to the frontend SDK.
    """
    gateway = get_billing_gateway(organisation)
    idempotency_key = f"payment:{organisation.pk}:{licence.pk}:{amount}:{uuid4()}"

    # Prevent duplicate orders for the same pending payment
    existing = Payment.objects.filter(
        organisation=organisation,
        licence=licence,
        status=Payment.Status.PENDING,
    ).first()
    if existing:
        return _order_options(existing, organisation, gateway)

    order = gateway.create_order(
        amount=amount,
        currency='INR' if organisation.country_code == 'IN' else 'USD',
        receipt=str(licence.pk),
        notes={'org_id': str(organisation.pk), 'licence_id': str(licence.pk)},
    )

    payment = Payment.objects.create(
        organisation=organisation,
        licence=licence,
        amount=amount,
        currency=order.currency,
        gateway=gateway.__class__.__name__.lower().replace('gateway', ''),
        gateway_order_id=order.gateway_order_id,
        status=Payment.Status.PENDING,
        idempotency_key=idempotency_key,
    )
    return _order_options(payment, organisation, order)
```

- [x] Add `process_payment_webhook(payload, signature, gateway_name)`:

```python
def process_payment_webhook(payload: bytes, signature: str, gateway_name: str) -> dict:
    gateway = get_gateway_by_name(gateway_name)

    if not gateway.verify_webhook_signature(payload, signature):
        raise WebhookSignatureError("Invalid webhook signature")

    event = gateway.parse_webhook_event(json.loads(payload))

    # Idempotent: skip if already processed
    payment = Payment.objects.filter(
        gateway_order_id=event.gateway_order_id
    ).select_for_update().first()

    if payment is None:
        logger.warning("webhook_unknown_order", order_id=event.gateway_order_id)
        return {'status': 'ignored'}

    if payment.status != Payment.Status.PENDING:
        return {'status': 'already_processed'}

    if event.status == 'SUCCESS':
        payment.status = Payment.Status.SUCCESS
        payment.gateway_payment_id = event.gateway_payment_id
        payment.completed_at = timezone.now()
        payment.save(update_fields=['status', 'gateway_payment_id', 'completed_at'])

        # Activate the licence
        activate_licence(payment.licence)

        # Generate invoice async
        generate_invoice_task.delay(str(payment.pk))

    elif event.status == 'FAILED':
        payment.status = Payment.Status.FAILED
        payment.failure_reason = str(event.raw_payload)
        payment.save(update_fields=['status', 'failure_reason'])

        # Notify org admin of failure
        notify_payment_failure(payment)

    return {'status': 'processed'}
```

## Task 4: Invoice Generation

- [x] Add `generate_invoice(payment: Payment) -> Invoice` in `organisations/services.py`:
  - Generate sequential `invoice_number` (e.g., `INV-2025-000042`)
  - Compute GST at 18% (CGST 9% + SGST 9% for same-state, IGST 18% for inter-state)
  - Store breakdown in `Invoice` model
  - Generate PDF via WeasyPrint with:
    - Clarisal logo and brand colours
    - "TAX INVOICE" header
    - Clarisal GST registration details
    - Organisation name, address, GSTIN
    - Line items: "SaaS Subscription — [plan] — [seat count] seats — [period]"
    - Subtotal, GST breakdown, Total in ₹
    - Payment reference number
  - Upload PDF to S3 and store key in `invoice.storage_key`
  - Return presigned download URL

- [x] Create `generate_invoice_task` Celery task that calls `generate_invoice` with retry:

```python
@app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def generate_invoice_task(self, payment_id: str):
    payment = Payment.objects.get(pk=payment_id)
    generate_invoice(payment)
```

## Task 5: API Endpoints

- [x] Register the following endpoints in `organisations/views.py` and `urls.py`:

```
POST   /api/v1/org/billing/payment-orders/       → create_payment_order (org-admin)
POST   /api/v1/billing/webhooks/razorpay/         → process_payment_webhook (no auth, HMAC)
POST   /api/v1/billing/webhooks/stripe/           → process_payment_webhook (no auth, HMAC)
GET    /api/v1/org/billing/invoices/              → list invoices (org-admin)
GET    /api/v1/org/billing/invoices/:id/download/ → presigned PDF URL (org-admin)
GET    /api/v1/ct/billing/                        → CT billing overview (CT-only)
```

- [x] The webhook endpoints use `require_POST` and HMAC verification — no Django CSRF needed (exempt them).
- [ ] Webhook endpoints must respond with HTTP 200 immediately and process async to avoid gateway timeouts.

## Task 6: Frontend — BillingPage (Org Admin)

- [x] Create `frontend/src/pages/org/BillingPage.tsx`:

```
Layout:
┌──────────────────────────────────────────────────────┐
│ Billing & Subscription                               │
├──────────────────────────────────────────────────────┤
│ Current Plan: Growth · 50 seats · ₹24,999/month      │
│ Status: ACTIVE  Next billing: 2026-05-01             │
│ [Upgrade Plan] [Manage Seats]                        │
├──────────────────────────────────────────────────────┤
│ Invoices                                             │
│  INV-2025-042  2025-04-01  ₹24,999   PAID  [PDF ↓]  │
│  INV-2025-011  2025-03-01  ₹24,999   PAID  [PDF ↓]  │
├──────────────────────────────────────────────────────┤
│ Payment Method: Razorpay (Last used: 2025-04-01)     │
│ [Update Payment Method]                              │
└──────────────────────────────────────────────────────┘
```

- [x] "Pay Now" button opens Razorpay checkout widget (using Razorpay JS SDK).
- [x] After payment success callback, poll `/api/v1/org/billing/payment-orders/:id/status/` until `SUCCESS`.
- [x] Invoice PDF download generates a presigned URL and opens in a new tab.

## Task 7: Frontend — CT Billing Page

- [x] Create `frontend/src/pages/ct/CtBillingPage.tsx`:
  - Table of all organisations with billing status
  - Filter: overdue, trial expiring, active subscriptions
  - Per-org: licence tier, seat count, last payment date, outstanding amount
  - CT actions: manually mark as paid, extend trial, suspend

## Task 8: Settings

- [x] Add to `settings/base.py`:

```python
# Payment gateway settings — loaded from environment variables
RAZORPAY_KEY_ID = env('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = env('RAZORPAY_KEY_SECRET', default='')
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')
BILLING_DEFAULT_CURRENCY = env('BILLING_DEFAULT_CURRENCY', default='INR')
BILLING_GST_RATE = Decimal('0.18')  # 18% GST
```

- [x] Add these variables to `.env.example` and deployment documentation.
- [x] Do NOT commit real keys — use env vars only.

## Task 9: Tests

- [x] Add tests in `organisations/tests/test_billing.py`:
  - `create_payment_order` creates a `Payment` record in PENDING state
  - `create_payment_order` called twice with same pending payment → returns existing order (no duplicate)
  - `process_payment_webhook` with valid signature and SUCCESS event → payment marked SUCCESS + licence activated
  - `process_payment_webhook` with invalid signature → `WebhookSignatureError` raised
  - `process_payment_webhook` called twice with same event → idempotent (second call returns `already_processed`)
  - `generate_invoice` creates PDF and stores S3 key
  - Invoice number is sequential and unique
