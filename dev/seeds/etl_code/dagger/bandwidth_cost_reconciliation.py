"""Bandwidth Cost Reconciliation - Cross-references billing invoices with metered bandwidth usage."""

from etls import bandwidth_invoices, stg_bgp_announcements

SUFFIXES = ["daily", "variances"]


class BandwidthCostReconciliation:
    def __init__(self):
        self.table = "fact_bandwidth_reconciled"
        self.destination_tables = ["fact_bandwidth_reconciled", "rpt_bandwidth_daily"]
        self.schedule = "Daily at 04:00 UTC"
        self.category = "Bandwidth/Billing"
        self.networks = ["backbone_core"]

    def extract(self, start_date, end_date):
        self.invoices = bandwidth_invoices(start_date, end_date).consume()
        self.routes = stg_bgp_announcements(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
