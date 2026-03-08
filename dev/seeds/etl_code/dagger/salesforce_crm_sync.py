"""Salesforce CRM Sync - Hourly sync of lead pipeline and account details."""

from etls import core_users_snapshot

SUFFIXES = ["leads", "opportunities", "contacts", "activities", "campaigns"]


class SalesforceCrmSync:
    def __init__(self):
        self.table = "crm_accounts"
        self.destination_tables = ["crm_accounts", "crm_leads", "crm_opportunities"]
        self.schedule = "Hourly"
        self.category = "Sales"
        self.networks = ["nightfall_revenue", "watchtower", "atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.users = core_users_snapshot(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
