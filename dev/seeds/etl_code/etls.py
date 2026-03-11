"""Table reader module — provides .consume() access to Iceberg tables.

Each function returns a TableReader that reads from the corresponding
Iceberg table, filtering by date range. Every table has a `date` column.
"""

from pyspark.sql import SparkSession


class TableReader:
    def __init__(self, iceberg_table, start_date, end_date):
        self.iceberg_table = iceberg_table
        self.start_date = start_date
        self.end_date = end_date

    def consume(self):
        spark = SparkSession.builder.getOrCreate()
        df = spark.table(f"iceberg.dagger.{self.iceberg_table}")
        df = df.filter(
            (df["date"] >= self.start_date.strftime("%Y-%m-%d"))
            & (df["date"] < self.end_date.strftime("%Y-%m-%d"))
        )
        return df


# --- Mapping: conceptual name -> Iceberg table (etl_name) ---

def switch_interface_snapshot(s, e):
    return TableReader("switch_port_collector", s, e)

def stg_bgp_announcements(s, e):
    return TableReader("bgp_route_sync", s, e)

def dns_zone_records(s, e):
    return TableReader("dns_record_sync", s, e)

def fact_netflow_records(s, e):
    return TableReader("netflow_capture", s, e)

def raw_syslog_events(s, e):
    return TableReader("syslog_event_stream", s, e)

def stg_dhcp_leases(s, e):
    return TableReader("dhcp_lease_sync", s, e)

def stg_http_access_logs(s, e):
    return TableReader("http_access_log_ingest", s, e)

def bandwidth_invoices(s, e):
    return TableReader("bandwidth_billing_aggregator", s, e)

def dim_device_fingerprint(s, e):
    return TableReader("device_fingerprint_enrichment", s, e)

def fact_bandwidth_reconciled(s, e):
    return TableReader("bandwidth_cost_reconciliation", s, e)

def ml_link_failure_features(s, e):
    return TableReader("link_failure_prediction", s, e)

def fact_packet_inspection(s, e):
    return TableReader("packet_inspection_enrichment", s, e)

def rpt_protocol_adoption(s, e):
    return TableReader("protocol_adoption_tracker", s, e)

def rpt_traffic_attribution(s, e):
    return TableReader("traffic_attribution_model", s, e)

def ml_threat_scores(s, e):
    return TableReader("threat_scoring_pipeline", s, e)

def ml_endpoint_activity_scores(s, e):
    return TableReader("endpoint_activity_scoring", s, e)

def rpt_peering_roi(s, e):
    return TableReader("peering_roi_calculator", s, e)

def rpt_capacity_forecast(s, e):
    return TableReader("capacity_planning_forecast", s, e)

def dim_enriched_mac_addresses(s, e):
    return TableReader("mac_address_enrichment", s, e)

def rpt_incident_analytics(s, e):
    return TableReader("incident_analytics_rollup", s, e)

def rpt_noc_dashboard(s, e):
    return TableReader("noc_dashboard_snapshot", s, e)

def fact_cdn_costs(s, e):
    return TableReader("cdn_cost_reconciler", s, e)

def rpt_weekly_digest(s, e):
    return TableReader("weekly_network_digest", s, e)

def rpt_handshake_analysis(s, e):
    return TableReader("handshake_completion_analysis", s, e)

def rpt_ab_routing(s, e):
    return TableReader("ab_routing_experiment_engine", s, e)

def rpt_device_onboarding(s, e):
    return TableReader("device_onboarding_monitor", s, e)

def rpt_traffic_class(s, e):
    return TableReader("traffic_class_segments", s, e)

def rpt_capacity_metrics(s, e):
    return TableReader("capacity_metrics_api", s, e)
