"""PostgreSQL Production DB - Nightly snapshot of the core application database."""

from etls import users, profiles, settings


class PostgresProductionDb:
    def __init__(self):
        self.table = "core_users_snapshot"
        self.destination_tables = ["core_users_snapshot", "core_profiles_snapshot"]
        self.schedule = "Daily at 03:00 UTC"
        self.category = "Core Backend"
        self.networks = ["core_infra", "product_insights"]

    def extract(self, start_date, end_date):
        user_data = users(start_date, end_date).consume()
        profile_data = profiles(start_date, end_date).consume()
        settings_data = settings(start_date, end_date).consume()
        return user_data, profile_data, settings_data

    def transform(self, data):
        pass

    def load(self, data):
        pass
