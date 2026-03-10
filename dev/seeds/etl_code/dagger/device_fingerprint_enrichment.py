"""Device Fingerprint Enrichment - Unified device profile from port, route, and DNS data."""

from etls import switch_interface_snapshot, stg_bgp_announcements, dns_zone_records

SUFFIXES = ["os_types", "vendors", "protocols_used", "risk_profiles"]


class DeviceFingerprintEnrichment:
    def __init__(self):
        self.table = "dim_device_fingerprint"
        self.destination_tables = ["dim_device_fingerprint", "dim_device_segments"]
        self.schedule = "Daily at 02:00 UTC"
        self.category = "Network Infrastructure"
        self.networks = ["backbone_core"]

    def extract(self, start_date, end_date):
        self.ports = switch_interface_snapshot(start_date, end_date).consume()
        self.routes = stg_bgp_announcements(start_date, end_date).consume()
        self.dns = dns_zone_records(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
