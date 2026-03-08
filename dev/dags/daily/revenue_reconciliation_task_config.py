"""Revenue Reconciliation — Daily billing vs orders cross-reference."""

needs = ["stripe_billing_aggregator", "shopify_sales_sync"]
prefers = []
writes_to = [
    "revenue_reconciliation",
    "revenue_reconciliation_daily",
    "revenue_reconciliation_variances",
]
