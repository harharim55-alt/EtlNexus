"""MAC Address Enrichment - Enriches MAC addresses with DHCP and HTTP access data."""

from etls import stg_dhcp_leases, stg_http_access_logs

SUFFIXES = ["vendor_lookups"]


class MacAddressEnrichment:
    def __init__(self):
        self.table = "dim_enriched_mac_addresses"
        self.destination_tables = ["dim_enriched_mac_addresses", "dim_mac_vendor_profiles"]
        self.schedule = "Daily at 02:30 UTC"
        self.category = "Address Management"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        self.leases = stg_dhcp_leases(start_date, end_date).consume()
        self.logs = stg_http_access_logs(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
