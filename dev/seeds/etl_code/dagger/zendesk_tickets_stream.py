"""Zendesk Tickets Stream - Real-time streaming of customer support tickets."""

from etls import tickets_stream, agent_events


class ZendeskTicketsStream:
    def __init__(self):
        self.table = "raw_zendesk_tickets"
        self.destination_tables = ["raw_zendesk_tickets", "raw_csat_scores"]
        self.schedule = "Real-time (Streaming)"
        self.category = "Support"
        self.networks = ["customer_ops", "support_pipeline"]

    def extract(self, start_date, end_date):
        tickets = tickets_stream(start_date, end_date).consume()
        agents = agent_events(start_date, end_date).consume()
        return tickets, agents

    def transform(self, data):
        pass

    def load(self, data):
        pass
