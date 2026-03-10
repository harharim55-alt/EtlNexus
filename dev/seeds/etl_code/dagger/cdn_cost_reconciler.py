"""CDN Cost Reconciler - Reconciles CDN provider billing with access log data."""

from etls import stg_http_access_logs

SUFFIXES = ["by_provider", "discrepancies"]


class CdnCostReconciler:
    def __init__(self):
        self.table = "rpt_cdn_cost_reconciled"
        self.destination_tables = ["rpt_cdn_cost_reconciled", "rpt_cdn_discrepancies"]
        self.schedule = "Daily at 02:30 UTC"
        self.category = "Bandwidth/Billing"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        self.logs = stg_http_access_logs(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
