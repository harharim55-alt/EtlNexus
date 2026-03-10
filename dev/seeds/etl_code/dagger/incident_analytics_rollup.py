"""Incident Analytics Rollup - Aggregates incident metrics with DNS context."""

from etls import raw_syslog_events, dns_zone_records

SUFFIXES = ["responder_performance"]


class IncidentAnalyticsRollup:
    def __init__(self):
        self.table = "rpt_incident_metrics"
        self.destination_tables = ["rpt_incident_metrics", "dim_responder_performance"]
        self.schedule = "Hourly"
        self.category = "Incident Management"
        self.networks = ["noc_sentinel"]

    def extract(self, start_date, end_date):
        self.events = raw_syslog_events(start_date, end_date).consume()
        self.dns = dns_zone_records(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
