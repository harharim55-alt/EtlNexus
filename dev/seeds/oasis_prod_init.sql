-- oasis_prod database schema and seed data.
--
-- Table: observer  (env: OASIS_OBSERVER_TABLE)
-- Each row is one data consumption event. The app counts a consumption when
-- storage_types = 'iceberg' (env: OASIS_OBSERVER_STORAGE_TYPE) and the row's
-- (data_source_name, data_name) match a pipeline's team (lowercased) + name
-- (task_id). The `ts` column is used for the card's date-range filter.

CREATE TABLE IF NOT EXISTS observer (
    id SERIAL PRIMARY KEY,
    data_source_name VARCHAR(255) NOT NULL,   -- team that produced the data (lowercase)
    data_name        VARCHAR(255) NOT NULL,   -- ETL name (pipeline task_id)
    storage_types    VARCHAR(50)  NOT NULL,   -- 'iceberg' | 'hdfs' | ...
    ts               TIMESTAMPTZ  NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observer_match ON observer (storage_types, data_source_name, data_name);
CREATE INDEX IF NOT EXISTS idx_observer_ts ON observer (ts);

-- ============================================================
-- Seed: per-pipeline consumption rows spread over the last 90 days.
-- Guarded so re-running the script is idempotent.
-- Each pipeline gets N 'iceberg' rows (the counted consumptions) plus a small
-- number of 'hdfs' rows that the iceberg filter must exclude.
-- (data_source_name, data_name) pairs mirror the app's (team.lower(), task_id).
-- ============================================================

DO $$
DECLARE
    r RECORD;
BEGIN
    IF (SELECT COUNT(*) FROM observer) > 0 THEN
        RETURN;
    END IF;

    FOR r IN
        SELECT * FROM (VALUES
            -- dagger
            ('dagger', 'PortScanCollector',              680),
            ('dagger', 'RouteTableRecon',                483),
            ('dagger', 'FlowInterceptor',                370),
            ('dagger', 'BandwidthAnalyzer',              225),
            ('dagger', 'BandwidthAnalyzer_tier_summary', 150),
            ('dagger', 'DeviceFingerprinter',            373),
            ('dagger', 'LinkAnomalyDetector',            480),
            ('dagger', 'BandwidthAuditReconciler',       243),
            ('dagger', 'NocThreatSnapshot',              272),
            ('dagger', 'NetworkThreatAssessment',        130),
            -- oasis
            ('oasis',  'DnsIntelSync',                   338),
            ('oasis',  'SyslogCollector',                340),
            ('oasis',  'IncidentForensicsRollup',        205),
            -- prism
            ('prism',  'ProtocolAnalyzer',               360),
            ('prism',  'TrafficClassifier',              325),
            ('prism',  'DeepPacketInspector',            283),
            ('prism',  'HandshakeAnalyzer',              195),
            ('prism',  'EndpointRiskScorer',             295),
            ('prism',  'ProvisioningAuditor',            130),
            ('prism',  'RoutingExperimentEngine',        185),
            -- vault
            ('vault',  'AccessLogCollector',             395),
            ('vault',  'DhcpLeaseRecon',                 215),
            ('vault',  'MacIntelEnrichment',             277),
            ('vault',  'ThreatHunterScorer',             380),
            ('vault',  'PeeringIntelCalculator',         265),
            ('vault',  'TrafficAttributionAnalyzer',     295),
            ('vault',  'CdnAuditReconciler',             203),
            ('vault',  'CapacityThreatForecast',         208),
            ('vault',  'WeeklyThreatDigest',             305)
        ) AS t(src, name, n)
    LOOP
        -- counted consumptions (iceberg)
        INSERT INTO observer (data_source_name, data_name, storage_types, ts)
        SELECT r.src, r.name, 'iceberg', NOW() - (random() * INTERVAL '90 days')
        FROM generate_series(1, r.n);

        -- non-iceberg rows the filter must exclude (~10%)
        INSERT INTO observer (data_source_name, data_name, storage_types, ts)
        SELECT r.src, r.name, 'hdfs', NOW() - (random() * INTERVAL '90 days')
        FROM generate_series(1, GREATEST(1, r.n / 10));
    END LOOP;
END $$;
