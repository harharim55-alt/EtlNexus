"""Mixpanel User Events - Raw user behavior events from web and mobile."""

from etls import raw_telemetry, core_backend


class MixpanelUserEvents:
    def __init__(self):
        self.table = "fact_user_events"
        self.destination_tables = ["fact_user_events", "dim_sessions"]
        self.schedule = "Every 4 Hours"
        self.category = "Analytics"
        self.networks = ["analytics_pipeline", "product_insights"]

    def extract(self, start_date, end_date):
        telemetry = raw_telemetry(start_date, end_date).consume()
        backend = core_backend(start_date, end_date).consume()
        return telemetry, backend

    def transform(self, data):
        pass

    def load(self, data):
        pass
