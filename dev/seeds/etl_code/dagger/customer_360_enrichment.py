"""Customer 360 Enrichment - Unified customer profile from user, sales, and CRM data."""

from etls import core_users_snapshot, stg_shopify_orders, crm_accounts

SUFFIXES = ["segments", "ltv", "interactions", "preferences"]


class Customer360Enrichment:
    def __init__(self):
        self.table = "dim_customer_360"
        self.destination_tables = ["dim_customer_360", "dim_customer_segments"]
        self.schedule = "Daily at 02:00 UTC"
        self.category = "Analytics"
        self.networks = ["atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.users = core_users_snapshot(start_date, end_date).consume()
        self.orders = stg_shopify_orders(start_date, end_date).consume()
        self.crm = crm_accounts(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
