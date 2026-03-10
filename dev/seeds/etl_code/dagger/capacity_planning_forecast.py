"""Capacity Planning Forecast - Network capacity forecast combining threat scores and attribution."""

from etls import ml_threat_scores, rpt_traffic_attribution

SUFFIXES = ["monthly"]


class CapacityPlanningForecast:
    def __init__(self):
        self.table = "rpt_capacity_forecast"
        self.destination_tables = ["rpt_capacity_forecast", "rpt_capacity_forecast_monthly"]
        self.schedule = "Daily at 03:00 UTC"
        self.category = "Predictive Analytics"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        self.threats = ml_threat_scores(start_date, end_date).consume()
        self.attribution = rpt_traffic_attribution(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
