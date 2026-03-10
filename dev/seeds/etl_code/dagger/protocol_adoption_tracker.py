"""Protocol Adoption Tracker - Per-protocol adoption rates and version curves."""

from etls import fact_packet_inspection

SUFFIXES = ["daily", "weekly", "by_version"]


class ProtocolAdoptionTracker:
    def __init__(self):
        self.table = "rpt_protocol_adoption"
        self.destination_tables = ["rpt_protocol_adoption", "rpt_protocol_adoption_weekly"]
        self.schedule = "Daily at 04:00 UTC"
        self.category = "Protocol Analytics"
        self.networks = ["application_mesh"]

    def extract(self, start_date, end_date):
        self.packets = fact_packet_inspection(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
