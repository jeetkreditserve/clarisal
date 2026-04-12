from django.urls import path

from .views import BillingWebhookView

urlpatterns = [
    path('webhooks/razorpay/', BillingWebhookView.as_view(gateway_name='RAZORPAY'), name='billing-webhook-razorpay'),
    path('webhooks/stripe/', BillingWebhookView.as_view(gateway_name='STRIPE'), name='billing-webhook-stripe'),
]
