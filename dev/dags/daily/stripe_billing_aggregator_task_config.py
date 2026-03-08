"""Stripe Billing Aggregator — Subscription lifecycle aggregation."""

needs = ["shopify_sales_sync"]
prefers = ["salesforce_crm_sync"]
writes_to = [
    "stripe_billing_aggregator",
    "stripe_billing_aggregator_subscriptions",
    "stripe_billing_aggregator_payments",
    "stripe_billing_aggregator_refunds",
]
