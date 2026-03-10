"""DNS Record Sync - Hourly sync of DNS zone records and resolution cache."""

from etls import switch_interface_snapshot

SUFFIXES = ["a_records", "cname_records", "mx_records", "txt_records", "ptr_records"]


class DnsRecordSync:
    def __init__(self):
        self.table = "dns_zone_records"
        self.destination_tables = ["dns_zone_records", "dns_pending_queries", "dns_resolution_cache"]
        self.schedule = "Hourly"
        self.category = "DNS/Resolution"
        self.networks = ["transit_exchange", "noc_sentinel", "backbone_core"]

    def extract(self, start_date, end_date):
        self.ports = switch_interface_snapshot(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
