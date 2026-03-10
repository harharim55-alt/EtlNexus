"""Bandwidth Billing Aggregator - Aggregates bandwidth metering and circuit billing events."""

from etls import stg_bgp_announcements, dns_zone_records

SUFFIXES = ["circuits", "metered_usage", "credits"]


class BandwidthBillingAggregator:
    def __init__(self):
        self.table = "bandwidth_invoices"
        self.destination_tables = ["bandwidth_invoices", "bandwidth_subscriptions"]
        self.schedule = "Hourly"
        self.category = "Bandwidth/Billing"
        self.networks = ["transit_exchange", "backbone_core"]

    def extract(self, start_date, end_date):
        self.routes = stg_bgp_announcements(start_date, end_date).consume()
        self.dns = dns_zone_records(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
