"""HTTP Access Log Ingest - Daily HTTP access log sessions and request events."""

SUFFIXES = ["sessions", "error_codes"]


class HttpAccessLogIngest:
    def __init__(self):
        self.table = "stg_http_access_logs"
        self.destination_tables = ["stg_http_access_logs", "stg_http_sessions"]
        self.schedule = "Daily at 02:00 UTC"
        self.category = "Traffic Analytics"
        self.networks = ["perimeter_defense"]

    def extract(self, start_date, end_date):
        pass

    def transform(self, data):
        pass

    def load(self, data):
        pass
