"""Billing Reports API - Serves reconciled revenue data to finance dashboards."""

from etls import fact_revenue_reconciled, finance_invoices

SUFFIXES = []


class BillingReportsApi:
    def __init__(self):
        self.table = ""
        self.destination_tables = []
        self.schedule = "On-demand (API)"
        self.category = "API"
        self.networks = ["atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.revenue = fact_revenue_reconciled(start_date, end_date).consume()
        self.invoices = finance_invoices(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
