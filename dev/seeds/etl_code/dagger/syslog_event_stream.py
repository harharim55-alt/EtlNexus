"""Syslog Event Stream - Real-time streaming of network syslog events."""

from etls import dns_zone_records

SUFFIXES = ["severity_scores", "facility_tags"]


class SyslogEventStream:
    def __init__(self):
        self.table = "raw_syslog_events"
        self.destination_tables = ["raw_syslog_events", "raw_severity_scores"]
        self.schedule = "Real-time (Streaming)"
        self.category = "Incident Management"
        self.networks = ["noc_sentinel"]

    def extract(self, start_date, end_date):
        self.dns = dns_zone_records(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
