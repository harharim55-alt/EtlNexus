"""Shopify Sales Sync ETL - Daily synchronization of e-commerce transactions."""

from etls import core_users_snapshot

SUFFIXES = ["customers", "products", "line_items", "refunds", "fulfillments", "discounts", "inventory"]


class ShopifySalesSync:
    def __init__(self):
        self.table = "stg_shopify_orders"
        self.destination_tables = ["stg_shopify_orders", "stg_shopify_customers"]
        self.schedule = "Daily at 00:00 UTC"
        self.category = "E-commerce"
        self.networks = ["nightfall_revenue", "atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.users = core_users_snapshot(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
