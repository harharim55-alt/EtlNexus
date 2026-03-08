"""Customer Insights API - Serves customer health scores and segment data."""

from etls import dim_customer_360, ml_churn_features

SUFFIXES = []


class CustomerInsightsApi:
    def __init__(self):
        self.table = ""
        self.destination_tables = []
        self.schedule = "On-demand (API)"
        self.category = "API"
        self.networks = ["atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.customers = dim_customer_360(start_date, end_date).consume()
        self.churn = ml_churn_features(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
