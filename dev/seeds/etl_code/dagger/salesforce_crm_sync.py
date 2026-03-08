"""Salesforce CRM Sync - Hourly sync of lead pipeline and account details."""

from etls import account, lead, opportunity


class SalesforceCrmSync:
    def __init__(self):
        self.table = "crm_accounts"
        self.destination_tables = ["crm_accounts", "crm_leads", "crm_opportunities"]
        self.schedule = "Hourly"
        self.category = "Sales"
        self.networks = ["revenue_daily", "crm_pipeline"]

    def extract(self, start_date, end_date):
        accounts = account(start_date, end_date).consume()
        leads = lead(start_date, end_date).consume()
        opps = opportunity(start_date, end_date).consume()
        return accounts, leads, opps

    def transform(self, data):
        pass

    def load(self, data):
        pass
