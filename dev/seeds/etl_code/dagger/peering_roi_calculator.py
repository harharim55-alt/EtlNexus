"""Peering ROI Calculator - Per-peer return on investment from attribution data."""

from etls import rpt_traffic_attribution

SUFFIXES = ["by_peer"]


class PeeringRoiCalculator:
    def __init__(self):
        self.table = "rpt_peering_roi"
        self.destination_tables = ["rpt_peering_roi", "rpt_peering_roi_by_interface"]
        self.schedule = "Daily at 03:00 UTC"
        self.category = "Traffic Engineering"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        self.attribution = rpt_traffic_attribution(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
