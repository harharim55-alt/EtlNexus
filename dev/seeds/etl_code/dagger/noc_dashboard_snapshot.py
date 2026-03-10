"""NOC Dashboard Snapshot - Top-level KPI rollup for network operations center."""

from etls import fact_bandwidth_reconciled, ml_link_failure_features

SUFFIXES = ["bandwidth_daily", "bandwidth_weekly", "bandwidth_monthly", "throughput", "capacity_total", "outage_daily", "outage_weekly", "latency", "jitter", "uptime", "mttr", "packets_per_second", "endpoints_active", "endpoints_total", "failover_7d", "failover_30d", "handshake_funnel", "traffic_cohort_analysis", "noc_board_summary"]


class NocDashboardSnapshot:
    def __init__(self):
        self.table = "rpt_noc_dashboard_kpis"
        self.destination_tables = ["rpt_noc_dashboard_kpis", "rpt_noc_weekly_summary"]
        self.schedule = "Daily at 06:00 UTC"
        self.category = "NOC Management"
        self.networks = ["backbone_core"]

    def extract(self, start_date, end_date):
        self.bandwidth = fact_bandwidth_reconciled(start_date, end_date).consume()
        self.failures = ml_link_failure_features(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
