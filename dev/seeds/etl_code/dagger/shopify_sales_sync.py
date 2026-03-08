"""Shopify Sales Sync ETL - Daily synchronization of e-commerce transactions."""

from etls import raw_orders, raw_customers, stripe_billing


class ShopifySalesSync:
    def __init__(self):
        self.table = "stg_shopify_orders"
        self.destination_tables = ["stg_shopify_orders", "stg_shopify_customers"]
        self.schedule = "Daily at 00:00 UTC"
        self.category = "E-commerce"
        self.networks = ["revenue_daily", "ecommerce_pipeline"]

    def extract(self, start_date, end_date):
        orders = raw_orders(start_date, end_date).consume()
        customers = raw_customers(start_date, end_date).consume()
        billing = stripe_billing(start_date, end_date).consume()
        return orders, customers, billing

    def transform(self, data):
        pass

    def load(self, data):
        pass
