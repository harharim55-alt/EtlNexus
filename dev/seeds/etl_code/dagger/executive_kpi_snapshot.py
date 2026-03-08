"""Executive KPI Snapshot - Top-level KPI rollup from revenue and churn data."""

from etls import fact_revenue_reconciled, ml_churn_features

SUFFIXES = [
    "revenue_daily", "revenue_weekly", "revenue_monthly",
    "mrr", "arr",
    "churn_daily", "churn_weekly",
    "nps", "csat",
    "ltv", "cac", "arpu",
    "dau", "mau",
    "retention_7d", "retention_30d",
    "conversion_funnel", "cohort_analysis", "board_summary",
]


class ExecutiveKpiSnapshot:
    def __init__(self):
        self.table = "rpt_executive_kpis"
        self.destination_tables = ["rpt_executive_kpis", "rpt_weekly_summary"]
        self.schedule = "Daily at 06:00 UTC"
        self.category = "Executive"
        self.networks = ["atlas_intelligence"]

    def extract(self, start_date, end_date):
        self.revenue = fact_revenue_reconciled(start_date, end_date).consume()
        self.churn = ml_churn_features(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
