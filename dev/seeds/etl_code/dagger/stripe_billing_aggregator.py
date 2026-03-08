"""Stripe Billing Aggregator - Aggregates subscription lifecycle events."""

from etls import mixpanel_events, invoices, subscriptions


class StripeBillingAggregator:
    def __init__(self):
        self.table = "finance_invoices"
        self.destination_tables = ["finance_invoices", "finance_subscriptions"]
        self.schedule = "Hourly"
        self.category = "Finance"
        self.networks = ["revenue_daily", "finance_pipeline"]

    def extract(self, start_date, end_date):
        events = mixpanel_events(start_date, end_date).consume()
        inv = invoices(start_date, end_date).consume()
        subs = subscriptions(start_date, end_date).consume()
        return events, inv, subs

    def transform(self, data):
        pass

    def load(self, data):
        pass
