"""Capacity Metrics API - Serves network capacity metrics to internal dashboards."""

from etls import fact_packet_inspection, rpt_protocol_adoption, ml_endpoint_activity_scores

SUFFIXES = []


class CapacityMetricsApi:
    def __init__(self):
        self.table = ""
        self.destination_tables = []
        self.schedule = "On-demand (API)"
        self.category = "Network APIs"
        self.networks = ["application_mesh"]

    def extract(self, start_date, end_date):
        self.packets = fact_packet_inspection(start_date, end_date).consume()
        self.adoption = rpt_protocol_adoption(start_date, end_date).consume()
        self.scoring = ml_endpoint_activity_scores(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
