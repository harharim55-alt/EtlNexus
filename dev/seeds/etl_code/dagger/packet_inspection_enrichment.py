"""Packet Inspection Enrichment - Enriches raw flow data with device context."""

from etls import fact_netflow_records, switch_interface_snapshot

SUFFIXES = ["flows", "payload_summaries"]


class PacketInspectionEnrichment:
    def __init__(self):
        self.table = "fact_packet_inspection"
        self.destination_tables = ["fact_packet_inspection", "dim_enriched_flows"]
        self.schedule = "Daily at 03:30 UTC"
        self.category = "Protocol Analytics"
        self.networks = ["application_mesh"]

    def extract(self, start_date, end_date):
        self.flows = fact_netflow_records(start_date, end_date).consume()
        self.ports = switch_interface_snapshot(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
