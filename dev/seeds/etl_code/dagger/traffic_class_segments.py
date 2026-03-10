"""Traffic Class Segments - Behavioral traffic classification from usage patterns."""

from etls import fact_packet_inspection, ml_endpoint_activity_scores

SUFFIXES = ["transitions", "qos_profiles"]


class TrafficClassSegments:
    def __init__(self):
        self.table = "dim_traffic_class_segments"
        self.destination_tables = ["dim_traffic_class_segments", "rpt_class_transitions"]
        self.schedule = "Daily at 05:00 UTC"
        self.category = "Protocol Analytics"
        self.networks = ["application_mesh"]

    def extract(self, start_date, end_date):
        self.packets = fact_packet_inspection(start_date, end_date).consume()
        self.scores = ml_endpoint_activity_scores(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
