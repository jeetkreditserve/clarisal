from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings

from .base import BillingGateway, BillingGatewayError, PaymentEvent, PaymentOrder


class StripeGateway(BillingGateway):
    gateway_name = 'STRIPE'

    def _stripe(self):
        if not settings.STRIPE_SECRET_KEY:
            raise BillingGatewayError('Stripe secret key is not configured.')
        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.api_version = settings.STRIPE_API_VERSION
        return stripe

    def create_order(self, amount: Decimal, currency: str, receipt: str, notes: dict[str, Any]) -> PaymentOrder:
        stripe = self._stripe()
        intent = stripe.PaymentIntent.create(
            amount=int((amount * Decimal('100')).quantize(Decimal('1'))),
            currency=currency.lower(),
            automatic_payment_methods={'enabled': True},
            metadata={**notes, 'receipt': receipt},
        )
        return PaymentOrder(
            gateway_order_id=intent['id'],
            amount=Decimal(str(intent.get('amount', 0))) / Decimal('100'),
            currency=str(intent.get('currency', currency)).upper(),
            gateway_options={
                'client_secret': intent.get('client_secret'),
                'payment_intent_id': intent['id'],
                'currency': str(intent.get('currency', currency)).upper(),
                'amount': intent.get('amount'),
            },
        )

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise BillingGatewayError('Stripe webhook secret is not configured.')
        stripe = self._stripe()
        try:
            stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
        except Exception:
            return False
        return True

    def parse_webhook_event(self, payload: dict[str, Any]) -> PaymentEvent:
        event_type = payload.get('type', '')
        data_object = ((payload.get('data') or {}).get('object') or {})
        gateway_order_id = data_object.get('id', '')
        gateway_payment_id = data_object.get('latest_charge') or gateway_order_id
        amount_minor = data_object.get('amount_received') or data_object.get('amount') or 0
        status = 'FAILED'
        if event_type == 'payment_intent.succeeded':
            status = 'SUCCESS'
        elif event_type == 'charge.refunded':
            status = 'REFUNDED'

        return PaymentEvent(
            gateway_payment_id=gateway_payment_id,
            gateway_order_id=gateway_order_id,
            status=status,
            amount=Decimal(str(amount_minor)) / Decimal('100'),
            raw_payload=payload,
        )

    def create_subscription(self, plan_id: str, customer_email: str) -> str:
        stripe = self._stripe()
        customer = stripe.Customer.create(email=customer_email)
        subscription = stripe.Subscription.create(
            customer=customer['id'],
            items=[{'price': plan_id}],
            payment_behavior='default_incomplete',
        )
        return subscription['id']
