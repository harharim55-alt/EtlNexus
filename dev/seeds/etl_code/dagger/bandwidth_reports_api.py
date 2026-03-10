"""Bandwidth Reports API - Serves reconciled bandwidth data to billing dashboards."""

from etls import fact_bandwidth_reconciled, bandwidth_invoices

SUFFIXES = []


class BandwidthReportsApi:
    def __init__(self):
        self.table = ""
        self.destination_tables = []
        self.schedule = "On-demand (API)"
        self.category = "Network APIs"
        self.networks = ["backbone_core"]

    def extract(self, start_date, end_date):
        self.bandwidth = fact_bandwidth_reconciled(start_date, end_date).consume()
        self.invoices = bandwidth_invoices(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
