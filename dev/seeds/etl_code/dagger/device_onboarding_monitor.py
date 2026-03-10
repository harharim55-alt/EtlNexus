"""Device Onboarding Monitor - Onboarding phase completion and rejection analysis."""

from etls import fact_packet_inspection

SUFFIXES = ["phases", "batches"]


class DeviceOnboardingMonitor:
    def __init__(self):
        self.table = "rpt_device_onboarding"
        self.destination_tables = ["rpt_device_onboarding", "rpt_onboarding_batches"]
        self.schedule = "Daily at 04:00 UTC"
        self.category = "Protocol Analytics"
        self.networks = ["application_mesh"]

    def extract(self, start_date, end_date):
        self.packets = fact_packet_inspection(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
