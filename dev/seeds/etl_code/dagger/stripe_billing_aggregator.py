"""Stripe Billing Aggregator - Aggregates subscription lifecycle events."""

from etls import stg_shopify_orders, crm_accounts

SUFFIXES = ["subscriptions", "payments", "refunds"]


class StripeBillingAggregator:
    def __init__(self):
        self.table = "finance_invoices"
        self.destination_tables = ["finance_invoices", "finance_subscriptions"]
        self.schedule = "Hourly"
        self.category = "Finance"
        self.networks = ["nightfall_revenue", "atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.orders = stg_shopify_orders(start_date, end_date).consume()
        self.crm = crm_accounts(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
