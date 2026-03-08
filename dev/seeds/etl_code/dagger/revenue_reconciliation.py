"""Revenue Reconciliation - Cross-references billing invoices with e-commerce orders."""

from etls import finance_invoices, stg_shopify_orders

SUFFIXES = ["daily", "variances"]


class RevenueReconciliation:
    def __init__(self):
        self.table = "fact_revenue_reconciled"
        self.destination_tables = ["fact_revenue_reconciled", "rpt_revenue_daily"]
        self.schedule = "Daily at 04:00 UTC"
        self.category = "Finance"
        self.networks = ["atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.invoices = finance_invoices(start_date, end_date).consume()
        self.orders = stg_shopify_orders(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
