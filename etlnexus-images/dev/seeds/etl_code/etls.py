"""Table reader module — provides .consume() access to Iceberg tables.

Each function returns a TableReader that reads from the corresponding
Iceberg table, filtering by date range. Every table has a `date` column.
Tables are organized by team namespace (dagger, prism, vault, oasis).
"""

from pyspark.sql import SparkSession


class TableReader:
    def __init__(self, namespace, iceberg_table, start_date, end_date):
        self.namespace = namespace
        self.iceberg_table = iceberg_table
        self.start_date = start_date
        self.end_date = end_date

    def consume(self):
        spark = SparkSession.builder.getOrCreate()
        df = spark.table(f"iceberg.{self.namespace}.{self.iceberg_table}")
        df = df.filter(
            (df["date"] >= self.start_date.strftime("%Y-%m-%d"))
            & (df["date"] < self.end_date.strftime("%Y-%m-%d"))
        )
        return df


# --- Dagger team tables ---

def switch_interface_snapshot(s, e):
    return TableReader("dagger", "PortScanCollector", s, e)

def stg_bgp_announcements(s, e):
    return TableReader("dagger", "RouteTableRecon", s, e)

def fact_netflow_records(s, e):
    return TableReader("dagger", "FlowInterceptor", s, e)

def dim_device_fingerprint(s, e):
    return TableReader("dagger", "DeviceFingerprinter", s, e)

def bandwidth_invoices(s, e):
    return TableReader("dagger", "BandwidthAnalyzer", s, e)

def ml_link_failure_features(s, e):
    return TableReader("dagger", "LinkAnomalyDetector", s, e)

def fact_bandwidth_reconciled(s, e):
    return TableReader("dagger", "BandwidthAuditReconciler", s, e)

def rpt_noc_dashboard(s, e):
    return TableReader("dagger", "NocThreatSnapshot", s, e)

def rpt_unified_network_assessment(s, e):
    return TableReader("dagger", "NetworkThreatAssessment", s, e)


# --- Prism team tables ---

def fact_packet_inspection(s, e):
    return TableReader("prism", "DeepPacketInspector", s, e)

def rpt_protocol_adoption(s, e):
    return TableReader("prism", "ProtocolAnalyzer", s, e)

def rpt_handshake_analysis(s, e):
    return TableReader("prism", "HandshakeAnalyzer", s, e)

def rpt_ab_routing(s, e):
    return TableReader("prism", "RoutingExperimentEngine", s, e)

def ml_endpoint_activity_scores(s, e):
    return TableReader("prism", "EndpointRiskScorer", s, e)

def rpt_device_onboarding(s, e):
    return TableReader("prism", "ProvisioningAuditor", s, e)

def rpt_traffic_class(s, e):
    return TableReader("prism", "TrafficClassifier", s, e)

def rpt_capacity_metrics(s, e):
    return TableReader("prism", "CapacityIntelApiDummy", s, e)


# --- Vault team tables ---

def stg_dhcp_leases(s, e):
    return TableReader("vault", "DhcpLeaseRecon", s, e)

def stg_http_access_logs(s, e):
    return TableReader("vault", "AccessLogCollector", s, e)

def rpt_traffic_attribution(s, e):
    return TableReader("vault", "TrafficAttributionAnalyzer", s, e)

def ml_threat_scores(s, e):
    return TableReader("vault", "ThreatHunterScorer", s, e)

def dim_enriched_mac_addresses(s, e):
    return TableReader("vault", "MacIntelEnrichment", s, e)

def fact_cdn_costs(s, e):
    return TableReader("vault", "CdnAuditReconciler", s, e)

def rpt_peering_roi(s, e):
    return TableReader("vault", "PeeringIntelCalculator", s, e)

def rpt_capacity_forecast(s, e):
    return TableReader("vault", "CapacityThreatForecast", s, e)

def rpt_weekly_digest(s, e):
    return TableReader("vault", "WeeklyThreatDigest", s, e)


# --- Oasis team tables ---

def dns_zone_records(s, e):
    return TableReader("oasis", "DnsIntelSync", s, e)

def raw_syslog_events(s, e):
    return TableReader("oasis", "SyslogCollector", s, e)

def rpt_incident_analytics(s, e):
    return TableReader("oasis", "IncidentForensicsRollup", s, e)


# --- Relay team tables ---

def asset_inventory_records(s, e):
    return TableReader("relay", "AssetInventorySnapshot", s, e)

def schema_compliance_results(s, e):
    return TableReader("relay", "SchemaComplianceChecker", s, e)

def field_frequency_profiles(s, e):
    return TableReader("relay", "FieldFrequencyProfiler", s, e)

def cross_team_audit_results(s, e):
    return TableReader("relay", "CrossTeamJoinAuditor", s, e)

def compliance_metrics_pivoted(s, e):
    return TableReader("relay", "ComplianceMetricsPivot", s, e)

def anomaly_pattern_results(s, e):
    return TableReader("relay", "AnomalyPatternMiner", s, e)

def quality_scorecard_results(s, e):
    return TableReader("relay", "DataQualityScorecard", s, e)
