"""Mixpanel User Events - Raw user behavior events from web and mobile."""

from etls import core_users_snapshot

SUFFIXES = []


class MixpanelUserEvents:
    def __init__(self):
        self.table = "fact_user_events"
        self.destination_tables = ["fact_user_events", "dim_sessions"]
        self.schedule = "Every 4 Hours"
        self.category = "Analytics"
        self.networks = ["pulse_360", "atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.users = core_users_snapshot(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
