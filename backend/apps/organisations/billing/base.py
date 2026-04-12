from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


class BillingGatewayError(ValueError):
    pass


class WebhookSignatureError(BillingGatewayError):
    pass


@dataclass(frozen=True)
class PaymentOrder:
    gateway_order_id: str
    amount: Decimal
    currency: str
    gateway_options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentEvent:
    gateway_payment_id: str
    gateway_order_id: str
    status: str
    amount: Decimal
    raw_payload: dict[str, Any]


class BillingGateway(ABC):
    gateway_name: str

    @abstractmethod
    def create_order(self, amount: Decimal, currency: str, receipt: str, notes: dict[str, Any]) -> PaymentOrder:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_webhook_event(self, payload: dict[str, Any]) -> PaymentEvent:
        raise NotImplementedError

    @abstractmethod
    def create_subscription(self, plan_id: str, customer_email: str) -> str:
        raise NotImplementedError


def resolve_billing_gateway_name(organisation: Any) -> str:
    configured = (getattr(organisation, 'billing_gateway', '') or '').upper()
    if configured and configured != 'MANUAL':
        return configured
    return 'RAZORPAY' if getattr(organisation, 'country_code', 'IN') == 'IN' else 'STRIPE'


def get_gateway_by_name(gateway_name: str) -> BillingGateway:
    resolved_name = gateway_name.upper()
    if resolved_name == 'RAZORPAY':
        from .razorpay import RazorpayGateway

        return RazorpayGateway()
    if resolved_name == 'STRIPE':
        from .stripe import StripeGateway

        return StripeGateway()
    raise BillingGatewayError(f'Unsupported billing gateway: {gateway_name}')


def get_billing_gateway(organisation: Any) -> BillingGateway:
    return get_gateway_by_name(resolve_billing_gateway_name(organisation))
