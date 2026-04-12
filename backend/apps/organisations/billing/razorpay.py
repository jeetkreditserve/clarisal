from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal
from typing import Any

from django.conf import settings

from .base import BillingGateway, BillingGatewayError, PaymentEvent, PaymentOrder


class RazorpayGateway(BillingGateway):
    gateway_name = 'RAZORPAY'

    def _client(self):
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise BillingGatewayError('Razorpay credentials are not configured.')
        import razorpay

        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    def create_order(self, amount: Decimal, currency: str, receipt: str, notes: dict[str, Any]) -> PaymentOrder:
        response = self._client().order.create(
            {
                'amount': int((amount * Decimal('100')).quantize(Decimal('1'))),
                'currency': currency,
                'receipt': receipt[:40],
                'notes': notes,
                'payment_capture': 1,
            }
        )
        return PaymentOrder(
            gateway_order_id=response['id'],
            amount=Decimal(str(response.get('amount', 0))) / Decimal('100'),
            currency=response.get('currency', currency),
            gateway_options={
                'key': settings.RAZORPAY_KEY_ID,
                'key_id': settings.RAZORPAY_KEY_ID,
                'order_id': response['id'],
                'currency': response.get('currency', currency),
                'amount': response.get('amount'),
            },
        )

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET
        if not secret:
            raise BillingGatewayError('Razorpay webhook secret is not configured.')
        digest = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        return bool(signature) and hmac.compare_digest(digest, signature)

    def parse_webhook_event(self, payload: dict[str, Any]) -> PaymentEvent:
        event_type = payload.get('event', '')
        event_payload = payload.get('payload') or {}
        payment_entity = (event_payload.get('payment') or {}).get('entity') or {}
        order_entity = (event_payload.get('order') or {}).get('entity') or {}

        gateway_order_id = payment_entity.get('order_id') or order_entity.get('id') or ''
        gateway_payment_id = payment_entity.get('id') or order_entity.get('id') or ''
        amount_paise = payment_entity.get('amount') or payment_entity.get('amount_paid') or order_entity.get('amount_paid') or 0
        status = 'FAILED'
        if event_type in {'payment.captured', 'order.paid'}:
            status = 'SUCCESS'
        elif event_type in {'refund.processed', 'payment.refunded'}:
            status = 'REFUNDED'

        return PaymentEvent(
            gateway_payment_id=gateway_payment_id,
            gateway_order_id=gateway_order_id,
            status=status,
            amount=Decimal(str(amount_paise)) / Decimal('100'),
            raw_payload=payload,
        )

    def create_subscription(self, plan_id: str, customer_email: str) -> str:
        response = self._client().subscription.create(
            {
                'plan_id': plan_id,
                'customer_notify': 1,
                'notes': {'customer_email': customer_email},
            }
        )
        return response['id']
