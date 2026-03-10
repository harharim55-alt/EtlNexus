"""Network Insights API - Serves device health scores and failure prediction data."""

from etls import dim_device_fingerprint, ml_link_failure_features

SUFFIXES = []


class NetworkInsightsApi:
    def __init__(self):
        self.table = ""
        self.destination_tables = []
        self.schedule = "On-demand (API)"
        self.category = "Network APIs"
        self.networks = ["backbone_core"]

    def extract(self, start_date, end_date):
        self.devices = dim_device_fingerprint(start_date, end_date).consume()
        self.failures = ml_link_failure_features(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
