-- oasis_prod database schema and seed data
-- Tables: data_interpaction_observeration_hdfs, data_interpaction_observeration_iceberg
-- These mirror the production observation tables used for data product usage metrics.

CREATE TABLE IF NOT EXISTS data_interpaction_observeration_hdfs (
    id SERIAL PRIMARY KEY,
    data_source_name VARCHAR(255) NOT NULL,
    data_name VARCHAR(255) NOT NULL,
    principal VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS data_interpaction_observeration_iceberg (
    id SERIAL PRIMARY KEY,
    data_source_name VARCHAR(255) NOT NULL,
    data_name VARCHAR(255) NOT NULL,
    principal VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obs_hdfs_product ON data_interpaction_observeration_hdfs (data_source_name, data_name);
CREATE INDEX IF NOT EXISTS idx_obs_hdfs_ts ON data_interpaction_observeration_hdfs (timestamp);
CREATE INDEX IF NOT EXISTS idx_obs_iceberg_product ON data_interpaction_observeration_iceberg (data_source_name, data_name);
CREATE INDEX IF NOT EXISTS idx_obs_iceberg_ts ON data_interpaction_observeration_iceberg (timestamp);

-- ============================================================
-- Seed data: realistic read observations spread over last 90 days
-- Principals are service accounts and analyst usernames
-- ============================================================

-- Helper: generate_series of timestamps across recent 90 days
-- We use a DO block to insert varied data programmatically.

DO $$
DECLARE
    ts TIMESTAMPTZ;
    i INT;
BEGIN

-- ============================================================
-- DAGGER team pipelines (HDFS-based)
-- ============================================================

-- PortScanCollector: heavily read by infra services and analysts
FOR i IN 1..320 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'PortScanCollector', 'svc-route-recon', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..180 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'PortScanCollector', 'svc-dns-intel', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..95 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'PortScanCollector', 'svc-flow-intercept', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..42 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'PortScanCollector', 'analyst.chen', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..28 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'PortScanCollector', 'analyst.martinez', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..15 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'PortScanCollector', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- RouteTableRecon
FOR i IN 1..210 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'RouteTableRecon', 'svc-bandwidth-analyzer', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..165 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'RouteTableRecon', 'svc-device-fingerprint', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..73 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'RouteTableRecon', 'svc-audit-reconciler', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..35 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'RouteTableRecon', 'analyst.park', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- FlowInterceptor
FOR i IN 1..260 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'FlowInterceptor', 'svc-anomaly-detect', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..88 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'FlowInterceptor', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..22 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'FlowInterceptor', 'analyst.singh', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- BandwidthAnalyzer
FOR i IN 1..140 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAnalyzer', 'svc-audit-reconciler', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..55 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAnalyzer', 'svc-bandwidth-api', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..30 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAnalyzer', 'analyst.chen', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- DeviceFingerprinter
FOR i IN 1..190 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'DeviceFingerprinter', 'svc-anomaly-detect', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..145 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'DeviceFingerprinter', 'svc-netintel-api', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..38 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'DeviceFingerprinter', 'analyst.park', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- LinkAnomalyDetector
FOR i IN 1..175 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'LinkAnomalyDetector', 'svc-noc-snapshot', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..220 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'LinkAnomalyDetector', 'svc-netintel-api', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..60 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'LinkAnomalyDetector', 'analyst.martinez', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..25 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'LinkAnomalyDetector', 'svc-threat-intel', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- BandwidthAuditReconciler
FOR i IN 1..130 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAuditReconciler', 'svc-noc-snapshot', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..95 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAuditReconciler', 'svc-bandwidth-api', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..18 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAuditReconciler', 'analyst.johnson', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- NocThreatSnapshot
FOR i IN 1..85 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NocThreatSnapshot', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..110 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NocThreatSnapshot', 'analyst.martinez', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..45 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NocThreatSnapshot', 'analyst.chen', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..32 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NocThreatSnapshot', 'svc-exec-reports', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- NetworkIntelApiDummy (API)
FOR i IN 1..350 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NetworkIntelApiDummy', 'svc-frontend-app', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..280 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NetworkIntelApiDummy', 'svc-mobile-gateway', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..120 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NetworkIntelApiDummy', 'svc-partner-sync', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- BandwidthAuditApiDummy (API)
FOR i IN 1..200 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAuditApiDummy', 'svc-billing-platform', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..85 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAuditApiDummy', 'svc-finance-export', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..40 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'BandwidthAuditApiDummy', 'analyst.johnson', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- NetworkThreatAssessment
FOR i IN 1..75 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NetworkThreatAssessment', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..55 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('dagger', 'NetworkThreatAssessment', 'analyst.singh', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- ============================================================
-- OASIS team pipelines (HDFS-based)
-- ============================================================

-- DnsIntelSync
FOR i IN 1..150 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'DnsIntelSync', 'svc-bandwidth-analyzer', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..110 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'DnsIntelSync', 'svc-device-fingerprint', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..48 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'DnsIntelSync', 'svc-forensics-rollup', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..30 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'DnsIntelSync', 'analyst.chen', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- SyslogCollector
FOR i IN 1..240 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'SyslogCollector', 'svc-forensics-rollup', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..65 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'SyslogCollector', 'svc-threat-intel', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..35 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'SyslogCollector', 'analyst.martinez', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- IncidentForensicsRollup
FOR i IN 1..90 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'IncidentForensicsRollup', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..70 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'IncidentForensicsRollup', 'analyst.park', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..45 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('oasis', 'IncidentForensicsRollup', 'svc-exec-reports', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- ============================================================
-- PRISM team pipelines (Iceberg-based)
-- ============================================================

-- ProtocolAnalyzer
FOR i IN 1..185 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'ProtocolAnalyzer', 'svc-traffic-classify', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..120 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'ProtocolAnalyzer', 'svc-deep-packet', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..55 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'ProtocolAnalyzer', 'analyst.singh', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- TrafficClassifier
FOR i IN 1..210 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'TrafficClassifier', 'svc-capacity-api', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..75 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'TrafficClassifier', 'svc-endpoint-risk', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..40 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'TrafficClassifier', 'analyst.martinez', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- DeepPacketInspector
FOR i IN 1..160 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'DeepPacketInspector', 'svc-handshake-analyzer', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..95 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'DeepPacketInspector', 'svc-threat-intel', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..28 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'DeepPacketInspector', 'analyst.chen', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- HandshakeAnalyzer
FOR i IN 1..130 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'HandshakeAnalyzer', 'svc-endpoint-risk', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..65 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'HandshakeAnalyzer', 'svc-provisioning-audit', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- EndpointRiskScorer
FOR i IN 1..170 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'EndpointRiskScorer', 'svc-routing-experiment', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..90 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'EndpointRiskScorer', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..35 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'EndpointRiskScorer', 'analyst.park', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- ProvisioningAuditor
FOR i IN 1..80 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'ProvisioningAuditor', 'svc-capacity-api', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..50 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'ProvisioningAuditor', 'analyst.johnson', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- RoutingExperimentEngine
FOR i IN 1..115 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'RoutingExperimentEngine', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..70 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'RoutingExperimentEngine', 'analyst.singh', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- CapacityIntelApiDummy (API)
FOR i IN 1..290 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'CapacityIntelApiDummy', 'svc-frontend-app', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..150 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('prism', 'CapacityIntelApiDummy', 'svc-mobile-gateway', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- ============================================================
-- VAULT team pipelines (mixed HDFS + Iceberg)
-- ============================================================

-- AccessLogCollector (HDFS)
FOR i IN 1..195 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'AccessLogCollector', 'svc-mac-intel', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..140 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'AccessLogCollector', 'svc-threat-hunter', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..60 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'AccessLogCollector', 'analyst.johnson', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- DhcpLeaseRecon (HDFS)
FOR i IN 1..105 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'DhcpLeaseRecon', 'svc-mac-intel', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..85 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'DhcpLeaseRecon', 'svc-traffic-attribution', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..25 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'DhcpLeaseRecon', 'analyst.park', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- MacIntelEnrichment (Iceberg)
FOR i IN 1..155 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'MacIntelEnrichment', 'svc-peering-intel', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..80 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'MacIntelEnrichment', 'svc-traffic-attribution', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..42 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'MacIntelEnrichment', 'analyst.chen', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- ThreatHunterScorer (Iceberg)
FOR i IN 1..200 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'ThreatHunterScorer', 'svc-capacity-threat', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..125 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'ThreatHunterScorer', 'svc-weekly-digest', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..55 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'ThreatHunterScorer', 'analyst.martinez', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- PeeringIntelCalculator (Iceberg)
FOR i IN 1..145 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'PeeringIntelCalculator', 'svc-cdn-audit', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..90 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'PeeringIntelCalculator', 'svc-capacity-threat', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..30 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'PeeringIntelCalculator', 'analyst.singh', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- TrafficAttributionAnalyzer (HDFS)
FOR i IN 1..170 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'TrafficAttributionAnalyzer', 'svc-cdn-audit', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..85 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'TrafficAttributionAnalyzer', 'svc-weekly-digest', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..40 LOOP
    INSERT INTO data_interpaction_observeration_hdfs (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'TrafficAttributionAnalyzer', 'analyst.johnson', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- CdnAuditReconciler (Iceberg)
FOR i IN 1..110 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'CdnAuditReconciler', 'svc-weekly-digest', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..65 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'CdnAuditReconciler', 'svc-exec-reports', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..28 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'CdnAuditReconciler', 'analyst.park', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- CapacityThreatForecast (Iceberg)
FOR i IN 1..95 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'CapacityThreatForecast', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..78 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'CapacityThreatForecast', 'svc-exec-reports', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..35 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'CapacityThreatForecast', 'analyst.chen', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

-- WeeklyThreatDigest (Iceberg)
FOR i IN 1..60 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'WeeklyThreatDigest', 'svc-exec-reports', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..120 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'WeeklyThreatDigest', 'analyst.martinez', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..85 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'WeeklyThreatDigest', 'analyst.johnson', NOW() - (random() * INTERVAL '90 days'));
END LOOP;
FOR i IN 1..40 LOOP
    INSERT INTO data_interpaction_observeration_iceberg (data_source_name, data_name, principal, timestamp)
    VALUES ('vault', 'WeeklyThreatDigest', 'svc-noc-dashboard', NOW() - (random() * INTERVAL '90 days'));
END LOOP;

END $$;
