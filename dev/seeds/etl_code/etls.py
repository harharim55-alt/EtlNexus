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
    return TableReader("SwitchPortCollector", s, e)

def stg_bgp_announcements(s, e):
    return TableReader("BgpRouteSync", s, e)

def dns_zone_records(s, e):
    return TableReader("DnsRecordSync", s, e)

def fact_netflow_records(s, e):
    return TableReader("NetflowCapture", s, e)

def raw_syslog_events(s, e):
    return TableReader("SyslogEventStream", s, e)

def stg_dhcp_leases(s, e):
    return TableReader("DhcpLeaseSync", s, e)

def stg_http_access_logs(s, e):
    return TableReader("HttpAccessLogIngest", s, e)

def bandwidth_invoices(s, e):
    return TableReader("BandwidthBillingAggregator", s, e)

def dim_device_fingerprint(s, e):
    return TableReader("DeviceFingerprintEnrichment", s, e)

def fact_bandwidth_reconciled(s, e):
    return TableReader("BandwidthCostReconciliation", s, e)

def ml_link_failure_features(s, e):
    return TableReader("LinkFailurePrediction", s, e)

def fact_packet_inspection(s, e):
    return TableReader("PacketInspectionEnrichment", s, e)

def rpt_protocol_adoption(s, e):
    return TableReader("ProtocolAdoptionTracker", s, e)

def rpt_traffic_attribution(s, e):
    return TableReader("TrafficAttributionModel", s, e)

def ml_threat_scores(s, e):
    return TableReader("ThreatScoringPipeline", s, e)

def ml_endpoint_activity_scores(s, e):
    return TableReader("EndpointActivityScoring", s, e)

def rpt_peering_roi(s, e):
    return TableReader("PeeringRoiCalculator", s, e)

def rpt_capacity_forecast(s, e):
    return TableReader("CapacityPlanningForecast", s, e)

def dim_enriched_mac_addresses(s, e):
    return TableReader("MacAddressEnrichment", s, e)

def rpt_incident_analytics(s, e):
    return TableReader("IncidentAnalyticsRollup", s, e)

def rpt_noc_dashboard(s, e):
    return TableReader("NocDashboardSnapshot", s, e)

def fact_cdn_costs(s, e):
    return TableReader("CdnCostReconciler", s, e)

def rpt_weekly_digest(s, e):
    return TableReader("WeeklyNetworkDigest", s, e)

def rpt_handshake_analysis(s, e):
    return TableReader("HandshakeCompletionAnalysis", s, e)

def rpt_ab_routing(s, e):
    return TableReader("AbRoutingExperimentEngine", s, e)

def rpt_device_onboarding(s, e):
    return TableReader("DeviceOnboardingMonitor", s, e)

def rpt_traffic_class(s, e):
    return TableReader("TrafficClassSegments", s, e)

def rpt_capacity_metrics(s, e):
    return TableReader("CapacityMetricsApiDummy", s, e)
