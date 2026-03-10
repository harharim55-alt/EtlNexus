"""Weekly Network Digest - Executive summary of network operations and peering performance."""

from etls import rpt_peering_roi, rpt_capacity_forecast, dim_enriched_mac_addresses

SUFFIXES = ["highlights"]


class WeeklyNetworkDigest:
    def __init__(self):
        self.table = "rpt_network_digest"
        self.destination_tables = ["rpt_network_digest", "rpt_digest_highlights"]
        self.schedule = "Daily at 03:30 UTC"
        self.category = "NOC Management"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        self.roi = rpt_peering_roi(start_date, end_date).consume()
        self.forecast = rpt_capacity_forecast(start_date, end_date).consume()
        self.macs = dim_enriched_mac_addresses(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
