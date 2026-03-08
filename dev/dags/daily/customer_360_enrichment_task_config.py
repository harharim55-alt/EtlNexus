"""Customer 360 Enrichment — Daily unified customer profile."""

needs = ["postgres_production_db", "shopify_sales_sync"]
prefers = ["salesforce_crm_sync"]
writes_to = [
    "customer_360_enrichment",
    "customer_360_enrichment_segments",
    "customer_360_enrichment_ltv",
    "customer_360_enrichment_interactions",
    "customer_360_enrichment_preferences",
]
