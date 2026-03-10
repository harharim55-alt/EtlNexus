"""DHCP Lease Sync - Ingests leases, pools, and reservations from DHCP server API."""

SUFFIXES = ["pools", "reservations"]


class DhcpLeaseSync:
    def __init__(self):
        self.table = "stg_dhcp_leases"
        self.destination_tables = ["stg_dhcp_leases", "stg_dhcp_pools"]
        self.schedule = "Daily at 02:00 UTC"
        self.category = "Address Management"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        pass

    def transform(self, data):
        pass

    def load(self, data):
        pass
