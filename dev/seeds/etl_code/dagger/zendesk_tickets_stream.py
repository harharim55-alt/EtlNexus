"""Zendesk Tickets Stream - Real-time streaming of customer support tickets."""

from etls import crm_accounts

SUFFIXES = ["csat_scores", "tags"]


class ZendeskTicketsStream:
    def __init__(self):
        self.table = "raw_zendesk_tickets"
        self.destination_tables = ["raw_zendesk_tickets", "raw_csat_scores"]
        self.schedule = "Real-time (Streaming)"
        self.category = "Support"
        self.networks = ["watchtower"]

    def extract(self, start_date, end_date):
        self.crm = crm_accounts(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
