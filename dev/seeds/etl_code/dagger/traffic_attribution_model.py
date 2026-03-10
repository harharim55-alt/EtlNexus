"""Traffic Attribution Model - Multi-hop traffic attribution across network interfaces."""

from etls import stg_http_access_logs, stg_dhcp_leases

SUFFIXES = ["interfaces", "hop_points"]


class TrafficAttributionModel:
    def __init__(self):
        self.table = "rpt_traffic_attribution"
        self.destination_tables = ["rpt_traffic_attribution", "rpt_attribution_interfaces"]
        self.schedule = "Daily at 02:30 UTC"
        self.category = "Traffic Engineering"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        self.logs = stg_http_access_logs(start_date, end_date).consume()
        self.leases = stg_dhcp_leases(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
