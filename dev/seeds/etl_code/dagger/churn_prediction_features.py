"""Churn Prediction Features - ML feature engineering from customer and behavior data."""

from etls import dim_customer_360, fact_user_events

SUFFIXES = ["health_scores", "segments", "weekly"]


class ChurnPredictionFeatures:
    def __init__(self):
        self.table = "ml_churn_features"
        self.destination_tables = ["ml_churn_features", "ml_customer_health_scores"]
        self.schedule = "Daily at 05:00 UTC"
        self.category = "Machine Learning"
        self.networks = ["atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.customers = dim_customer_360(start_date, end_date).consume()
        self.events = fact_user_events(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
