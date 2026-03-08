"""Support Analytics Rollup - Aggregates support metrics with customer context."""

from etls import raw_zendesk_tickets, crm_accounts

SUFFIXES = ["agent_performance"]


class SupportAnalyticsRollup:
    def __init__(self):
        self.table = "rpt_support_metrics"
        self.destination_tables = ["rpt_support_metrics", "dim_agent_performance"]
        self.schedule = "Hourly"
        self.category = "Support"
        self.networks = ["watchtower"]

    def extract(self, start_date, end_date):
        self.tickets = raw_zendesk_tickets(start_date, end_date).consume()
        self.crm = crm_accounts(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
