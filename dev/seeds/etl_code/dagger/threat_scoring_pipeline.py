"""Threat Scoring Pipeline - ML-based threat qualification from DHCP lease data."""

from etls import stg_dhcp_leases

SUFFIXES = ["indicators", "scores"]


class ThreatScoringPipeline:
    def __init__(self):
        self.table = "ml_threat_scores"
        self.destination_tables = ["ml_threat_scores", "ml_threat_features"]
        self.schedule = "Daily at 02:30 UTC"
        self.category = "Predictive Analytics"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        self.leases = stg_dhcp_leases(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
