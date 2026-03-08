"""PostgreSQL Production DB - Nightly snapshot of the core application database."""

SUFFIXES = ["profiles", "orgs", "sessions", "plans"]


class PostgresProductionDb:
    def __init__(self):
        self.table = "core_users_snapshot"
        self.destination_tables = ["core_users_snapshot", "core_profiles_snapshot"]
        self.schedule = "Daily at 03:00 UTC"
        self.category = "Core Backend"
        self.networks = ["pulse_360", "nightfall_revenue", "atlas_intelligence"]

    def extract(self, start_date, end_date):
        pass

    def transform(self, data):
        pass

    def load(self, data):
        pass
