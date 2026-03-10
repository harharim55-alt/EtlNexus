"""Endpoint Activity Scoring - Per-endpoint activity score from traffic signals."""

from etls import fact_packet_inspection, dim_device_fingerprint

SUFFIXES = ["daily", "tiers"]


class EndpointActivityScoring:
    def __init__(self):
        self.table = "ml_endpoint_activity_scores"
        self.destination_tables = ["ml_endpoint_activity_scores", "dim_endpoint_segments"]
        self.schedule = "Daily at 04:30 UTC"
        self.category = "Predictive Analytics"
        self.networks = ["application_mesh"]

    def extract(self, start_date, end_date):
        self.packets = fact_packet_inspection(start_date, end_date).consume()
        self.devices = dim_device_fingerprint(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
