"""Seed Iceberg tables with realistic network-themed sample data."""

import os
import random
import sys
import time
import urllib.request
import urllib.error

os.umask(0)
from datetime import date, datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

CATALOG_URL = os.environ.get("ICEBERG_CATALOG_URI", "http://iceberg-rest:8181")
SEED = 42
random.seed(SEED)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DATES = [date(2026, 3, d) for d in range(7, 22)]  # 15 days: Mar 7-21
HOURS = list(range(24))


def rand_ip_10():
    return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def rand_ip_192():
    return f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"


def rand_ip_172():
    return f"172.16.{random.randint(0,15)}.{random.randint(1,254)}"


def rand_ip():
    return random.choice([rand_ip_10, rand_ip_192, rand_ip_172])()


def rand_mac():
    return ":".join(f"{random.randint(0,255):02X}" for _ in range(6))


def rand_ts(d):
    """Random timestamp on a given date."""
    return datetime(d.year, d.month, d.day,
                    random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))


def rand_ts_hour(d, h):
    """Random timestamp on a given date and hour."""
    return datetime(d.year, d.month, d.day, h, random.randint(0, 59), random.randint(0, 59))


HOSTNAMES = [
    "switch-01", "switch-02", "switch-03", "switch-04",
    "router-edge-01", "router-edge-02", "router-core-01", "router-core-02",
    "fw-dmz-01", "fw-dmz-02", "fw-internal-01",
    "ap-floor1-01", "ap-floor2-01", "ap-floor3-01",
    "server-web-01", "server-db-01", "server-app-01", "server-cache-01",
    "lb-front-01", "lb-front-02",
]

PROTOCOLS = ["TCP", "UDP", "ICMP", "HTTP", "HTTPS", "DNS", "SSH", "SNMP"]
STATUSES = ["active", "inactive", "pending", "failed", "success"]
PORT_SPEEDS = ["1Gbps", "10Gbps", "25Gbps", "40Gbps", "100Gbps"]
VLANS = [10, 20, 30, 40, 50, 100, 200, 300, 400, 500]
OS_FINGERPRINTS = ["Linux 5.15", "Windows 11", "Cisco IOS 17.6", "Junos 23.2",
                   "FreeBSD 14", "Ubuntu 22.04", "Arista EOS 4.30", "PAN-OS 11.1"]
DEVICE_CLASSES = ["switch", "router", "firewall", "access_point", "server",
                  "workstation", "printer", "iot_sensor", "ip_phone"]
ZONES = ["corp.example.com", "infra.example.com", "dmz.example.com",
         "edge.example.com", "lab.example.com"]
RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "PTR", "SRV"]
FACILITIES = ["kern", "user", "daemon", "auth", "syslog", "local0", "local1", "local7"]
SEVERITIES = ["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]
METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
USER_AGENTS = [
    "Mozilla/5.0 (Linux; NetMon/3.1)",
    "curl/8.4.0",
    "python-requests/2.31",
    "Prometheus/2.48",
    "Grafana/10.2",
    "Nagios-Plugins/2.4",
]
REQUEST_PATHS = [
    "/api/v1/devices", "/api/v1/flows", "/api/v1/health",
    "/api/v1/interfaces", "/api/v1/alerts", "/api/v2/topology",
    "/metrics", "/healthz", "/status", "/api/v1/config",
]
CDN_PROVIDERS = ["CloudFlare", "Akamai", "Fastly", "AWS CloudFront", "Azure CDN"]
CDN_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "eu-central-1",
               "ap-southeast-1", "ap-northeast-1"]
BILLING_TIERS = ["basic", "standard", "premium", "enterprise", "burstable"]
TRAFFIC_CLASSES = ["real-time", "interactive", "bulk", "best-effort", "scavenger"]
HANDSHAKE_TYPES = ["TCP", "TLS 1.2", "TLS 1.3", "QUIC", "DTLS"]
PEER_NAMES = [
    "Level3-AS3356", "Cogent-AS174", "Telia-AS1299", "NTT-AS2914",
    "Lumen-AS3549", "GTT-AS3257", "Zayo-AS6461", "Hurricane-AS6939",
    "PCCW-AS3491", "Tata-AS6453",
]
INTERFACES = [
    "eth0/0", "eth0/1", "eth1/0", "eth1/1", "ge-0/0/0", "ge-0/0/1",
    "xe-0/0/0", "xe-0/0/1", "et-0/0/0", "Po1", "Po2",
]
ONBOARDING_PHASES = [
    "discovery", "authentication", "policy_assignment",
    "vlan_assignment", "compliance_check", "provisioned",
]
RISK_BUCKETS = ["low", "medium", "high", "critical"]
POOL_NAMES = ["mgmt-pool", "server-pool", "iot-pool", "guest-pool",
              "voice-pool", "data-pool", "dmz-pool"]
LEASE_STATES = ["active", "expired", "reserved", "released", "declined"]
MODEL_TYPES = ["first-hop", "last-hop", "linear", "time-decay", "shapley"]


# ---------------------------------------------------------------------------
# Wait
# ---------------------------------------------------------------------------

def wait_for_catalog(max_retries=30, delay=2):
    """Wait until the Iceberg REST catalog is ready."""
    for i in range(max_retries):
        try:
            req = urllib.request.Request(f"{CATALOG_URL}/v1/config")
            with urllib.request.urlopen(req, timeout=5):
                print("Iceberg REST catalog is ready")
                return True
        except (urllib.error.URLError, OSError):
            print(f"Waiting for catalog... ({i + 1}/{max_retries})")
            time.sleep(delay)
    print("ERROR: Iceberg catalog not available after retries")
    return False


# ---------------------------------------------------------------------------
# Spark
# ---------------------------------------------------------------------------

def create_spark_session():
    spark = (
        SparkSession.builder
        .appName("EtlNexus-DataSeed")
        .master("local[1]")
        .config("spark.jars", "/opt/airflow/jars/iceberg-spark-runtime.jar")
        .config("spark.sql.catalog.iceberg",
                "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.iceberg.type", "rest")
        .config("spark.sql.catalog.iceberg.uri", "http://iceberg-rest:8181")
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.driver.memory", "1g")
        .config("spark.ui.enabled", "false")
        .config("spark.hadoop.fs.permissions.umask-mode", "000")
        .getOrCreate()
    )
    return spark


def seed_table(spark, namespace, table_name, schema, rows):
    df = spark.createDataFrame(rows, schema)
    df.writeTo(f"iceberg.{namespace}.{table_name}").using("iceberg").createOrReplace()
    print(f"  Seeded {namespace}.{table_name}: {len(rows)} rows")


# ---------------------------------------------------------------------------
# Data generators  (one function per table)
# ---------------------------------------------------------------------------

def gen_bgp_route_sync():
    schema = StructType([
        StructField("route_id", LongType()),
        StructField("prefix", StringType()),
        StructField("next_hop", StringType()),
        StructField("as_path", StringType()),
        StructField("origin", StringType()),
        StructField("status", StringType()),
        StructField("peer_id", LongType()),
        StructField("synced_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    rid = 1
    for d in DATES:
        for _ in range(175):
            prefix_net = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.0/{random.choice([8,16,24])}"
            as_path = " ".join(str(random.randint(100, 65000)) for _ in range(random.randint(2, 6)))
            rows.append((
                rid, prefix_net, rand_ip(), as_path,
                random.choice(["igp", "egp", "incomplete"]),
                random.choice(["established", "idle", "active", "openconfirm"]),
                random.randint(1, 50), rand_ts(d), d,
            ))
            rid += 1
    return schema, rows


def gen_syslog_event_stream():
    schema = StructType([
        StructField("event_id", LongType()),
        StructField("source_host", StringType()),
        StructField("facility", StringType()),
        StructField("severity", StringType()),
        StructField("message", StringType()),
        StructField("priority", StringType()),
        StructField("event_time", TimestampType()),
        StructField("received_at", TimestampType()),
        StructField("date", DateType()),
        StructField("hourkey", IntegerType()),
    ])
    messages = [
        "Interface {} went down", "BGP session reset with peer {}",
        "Authentication failure from {}", "Link flap detected on {}",
        "CPU utilization exceeded 90% on {}", "Memory threshold warning on {}",
        "Firewall rule {} matched", "DHCP pool {} exhausted",
        "NTP sync lost on {}", "OSPF adjacency changed on {}",
    ]
    rows = []
    eid = 1
    for d in DATES:
        for h in HOURS:
            for _ in range(80):
                ts = rand_ts_hour(d, h)
                rows.append((
                    eid, random.choice(HOSTNAMES),
                    random.choice(FACILITIES), random.choice(SEVERITIES),
                    random.choice(messages).format(random.choice(HOSTNAMES)),
                    str(random.randint(0, 191)),
                    ts, ts + timedelta(seconds=random.randint(0, 3)),
                    d, h,
                ))
                eid += 1
    return schema, rows


def gen_bandwidth_billing_aggregator():
    schema = StructType([
        StructField("invoice_id", StringType()),
        StructField("circuit_id", StringType()),
        StructField("subscription_id", StringType()),
        StructField("bandwidth_allocated_mbps", DoubleType()),
        StructField("bandwidth_used_mbps", DoubleType()),
        StructField("billing_tier", StringType()),
        StructField("status", StringType()),
        StructField("period_start", TimestampType()),
        StructField("period_end", TimestampType()),
        StructField("created_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    for d in DATES:
        for i in range(150):
            alloc = random.choice([100.0, 500.0, 1000.0, 10000.0])
            used = round(alloc * random.uniform(0.1, 0.95), 2)
            ts = rand_ts(d)
            rows.append((
                f"INV-{d.month:02d}{d.day:02d}-{i:04d}",
                f"CIR-{random.randint(1000,9999)}", f"SUB-{random.randint(100,999)}",
                alloc, used, random.choice(BILLING_TIERS),
                random.choice(["billed", "pending", "overdue", "paid"]),
                datetime(d.year, d.month, d.day, 0, 0, 0),
                datetime(d.year, d.month, d.day, 23, 59, 59),
                ts, d,
            ))
    return schema, rows


def gen_netflow_capture():
    schema = StructType([
        StructField("flow_id", StringType()),
        StructField("src_ip", StringType()),
        StructField("dst_ip", StringType()),
        StructField("capture_time", TimestampType()),
        StructField("session_id", StringType()),
        StructField("protocol", StringType()),
        StructField("bytes_transferred", LongType()),
        StructField("collected_at", TimestampType()),
        StructField("date", DateType()),
        StructField("hourkey", IntegerType()),
    ])
    rows = []
    fid = 1
    for d in DATES:
        for h in HOURS:
            for _ in range(80):
                ts = rand_ts_hour(d, h)
                rows.append((
                    f"flow-{fid:08d}", rand_ip(), rand_ip(),
                    ts, f"sess-{random.randint(10000,99999)}",
                    random.choice(PROTOCOLS),
                    random.randint(64, 1500000000),
                    ts + timedelta(seconds=random.randint(0, 5)),
                    d, h,
                ))
                fid += 1
    return schema, rows


def gen_dns_record_sync():
    schema = StructType([
        StructField("record_id", StringType()),
        StructField("zone_name", StringType()),
        StructField("record_type", StringType()),
        StructField("ttl", LongType()),
        StructField("record_value", StringType()),
        StructField("status", StringType()),
        StructField("created_date", DateType()),
        StructField("last_modified_date", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    rid = 1
    for d in DATES:
        for _ in range(150):
            rtype = random.choice(RECORD_TYPES)
            if rtype == "A":
                val = rand_ip()
            elif rtype == "AAAA":
                val = "2001:db8:" + ":".join(f"{random.randint(0,65535):04x}" for _ in range(6))
            elif rtype == "CNAME":
                val = f"{random.choice(HOSTNAMES)}.{random.choice(ZONES)}"
            elif rtype == "MX":
                val = f"{random.randint(10,50)} mail.{random.choice(ZONES)}"
            else:
                val = f"v=spf1 include:{random.choice(ZONES)} ~all"
            rows.append((
                f"rec-{rid:06d}", random.choice(ZONES), rtype,
                random.choice([60, 300, 3600, 86400]),
                val, random.choice(["active", "pending", "stale"]),
                d, rand_ts(d), d,
            ))
            rid += 1
    return schema, rows


def gen_switch_port_collector():
    schema = StructType([
        StructField("switch_id", LongType()),
        StructField("port_number", StringType()),
        StructField("mac_address", StringType()),
        StructField("collected_at", TimestampType()),
        StructField("last_state_change", TimestampType()),
        StructField("is_active", BooleanType()),
        StructField("port_speed", StringType()),
        StructField("vlan_id", LongType()),
        StructField("date", DateType()),
    ])
    rows = []
    for d in DATES:
        for _ in range(500):
            ts = rand_ts(d)
            rows.append((
                random.randint(1, 20),
                f"Gi{random.randint(0,3)}/{random.randint(0,47)}",
                rand_mac(), ts,
                ts - timedelta(hours=random.randint(0, 72)),
                random.random() > 0.15,
                random.choice(PORT_SPEEDS),
                random.choice(VLANS), d,
            ))
    return schema, rows


def gen_device_fingerprint_enrichment():
    schema = StructType([
        StructField("device_id", StringType()),
        StructField("mac_address", StringType()),
        StructField("hostname", StringType()),
        StructField("open_ports", LongType()),
        StructField("os_fingerprint", StringType()),
        StructField("device_class", StringType()),
        StructField("switch_port", StringType()),
        StructField("enriched_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    did = 1
    for d in DATES:
        for _ in range(400):
            rows.append((
                f"dev-{did:06d}", rand_mac(),
                random.choice(HOSTNAMES),
                random.randint(1, 30),
                random.choice(OS_FINGERPRINTS),
                random.choice(DEVICE_CLASSES),
                f"Gi{random.randint(0,3)}/{random.randint(0,47)}",
                rand_ts(d), d,
            ))
            did += 1
    return schema, rows


def gen_bandwidth_cost_reconciliation():
    schema = StructType([
        StructField("reconciliation_id", StringType()),
        StructField("circuit_id", StringType()),
        StructField("invoice_id", StringType()),
        StructField("metered_bytes", DoubleType()),
        StructField("billed_bytes", DoubleType()),
        StructField("variance_pct", DoubleType()),
        StructField("status", StringType()),
        StructField("reconciled_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    rid = 1
    for d in DATES:
        for _ in range(125):
            metered = round(random.uniform(1e9, 1e12), 2)
            variance = round(random.uniform(-15.0, 15.0), 2)
            billed = round(metered * (1 + variance / 100), 2)
            rows.append((
                f"recon-{rid:06d}", f"CIR-{random.randint(1000,9999)}",
                f"INV-{d.month:02d}{d.day:02d}-{random.randint(0,599):04d}",
                metered, billed, variance,
                random.choice(["matched", "variance", "disputed", "resolved"]),
                rand_ts(d), d,
            ))
            rid += 1
    return schema, rows


def gen_link_failure_prediction():
    schema = StructType([
        StructField("link_id", StringType()),
        StructField("hours_since_last_flap", LongType()),
        StructField("avg_error_rate", DoubleType()),
        StructField("crc_errors_30d", LongType()),
        StructField("packet_loss_events_90d", LongType()),
        StructField("failure_probability", DoubleType()),
        StructField("health_score", DoubleType()),
        StructField("scored_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    lid = 1
    for d in DATES:
        for _ in range(150):
            fail_prob = round(random.uniform(0.0, 1.0), 4)
            health = round(1.0 - fail_prob + random.uniform(-0.1, 0.1), 4)
            health = max(0.0, min(1.0, health))
            rows.append((
                f"link-{lid:05d}",
                random.randint(1, 8760),
                round(random.uniform(0.0, 0.05), 6),
                random.randint(0, 5000),
                random.randint(0, 200),
                fail_prob, health, rand_ts(d), d,
            ))
            lid += 1
    return schema, rows


def gen_incident_analytics_rollup():
    schema = StructType([
        StructField("period", StringType()),
        StructField("total_incidents", LongType()),
        StructField("avg_resolution_minutes", DoubleType()),
        StructField("severity_score", DoubleType()),
        StructField("responder_id", StringType()),
        StructField("sla_met_pct", DoubleType()),
        StructField("escalation_rate", DoubleType()),
        StructField("computed_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    responders = [f"noc-eng-{i:02d}" for i in range(1, 16)]
    for d in DATES:
        for _ in range(125):
            rows.append((
                f"{d.isoformat()}", random.randint(1, 80),
                round(random.uniform(5.0, 480.0), 1),
                round(random.uniform(1.0, 10.0), 2),
                random.choice(responders),
                round(random.uniform(70.0, 100.0), 1),
                round(random.uniform(0.0, 0.35), 3),
                rand_ts(d), d,
            ))
    return schema, rows


def gen_noc_dashboard_snapshot():
    schema = StructType([
        StructField("snapshot_date", DateType()),
        StructField("total_bandwidth_gbps", DoubleType()),
        StructField("peak_throughput_gbps", DoubleType()),
        StructField("active_endpoints", LongType()),
        StructField("link_failure_rate", DoubleType()),
        StructField("avg_health_score", DoubleType()),
        StructField("avg_latency_ms", DoubleType()),
        StructField("generated_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    for d in DATES:
        for _ in range(150):
            total_bw = round(random.uniform(50.0, 800.0), 2)
            rows.append((
                d, total_bw,
                round(total_bw * random.uniform(0.7, 0.99), 2),
                random.randint(500, 15000),
                round(random.uniform(0.0, 0.05), 4),
                round(random.uniform(0.7, 1.0), 3),
                round(random.uniform(0.5, 120.0), 2),
                rand_ts(d), d,
            ))
    return schema, rows


def gen_packet_inspection_enrichment():
    schema = StructType([
        StructField("packet_id", StringType()),
        StructField("src_ip", StringType()),
        StructField("protocol", StringType()),
        StructField("capture_time", TimestampType()),
        StructField("session_id", StringType()),
        StructField("application_layer", StringType()),
        StructField("port_speed", StringType()),
        StructField("vlan_id", LongType()),
        StructField("first_seen_date", DateType()),
        StructField("enriched_at", TimestampType()),
        StructField("date", DateType()),
    ])
    app_layers = ["HTTP/2", "gRPC", "WebSocket", "MQTT", "AMQP", "DNS-over-HTTPS",
                  "QUIC", "TLS 1.3", "SSH", "SNMP v3"]
    rows = []
    pid = 1
    for d in DATES:
        for _ in range(175):
            ts = rand_ts(d)
            rows.append((
                f"pkt-{pid:08d}", rand_ip(),
                random.choice(PROTOCOLS), ts,
                f"sess-{random.randint(10000,99999)}",
                random.choice(app_layers),
                random.choice(PORT_SPEEDS),
                random.choice(VLANS),
                d - timedelta(days=random.randint(0, 30)),
                ts + timedelta(milliseconds=random.randint(1, 500)),
                d,
            ))
            pid += 1
    return schema, rows


def gen_protocol_adoption_tracker():
    schema = StructType([
        StructField("protocol_name", StringType()),
        StructField("report_date", DateType()),
        StructField("unique_endpoints", LongType()),
        StructField("first_seen_count", LongType()),
        StructField("daily_active", LongType()),
        StructField("weekly_active", LongType()),
        StructField("adoption_rate", DoubleType()),
        StructField("computed_at", TimestampType()),
        StructField("date", DateType()),
    ])
    protocols_ext = PROTOCOLS + ["QUIC", "gRPC", "MQTT", "AMQP", "CoAP",
                                  "Modbus-TCP", "BACnet", "ZigBee"]
    rows = []
    for d in DATES:
        for proto in protocols_ext:
            unique = random.randint(100, 10000)
            daily = int(unique * random.uniform(0.3, 0.9))
            weekly = int(unique * random.uniform(0.6, 1.0))
            rows.append((
                proto, d, unique,
                random.randint(0, 200), daily, weekly,
                round(random.uniform(0.01, 0.95), 4),
                rand_ts(d), d,
            ))
    return schema, rows


def gen_handshake_completion_analysis():
    schema = StructType([
        StructField("handshake_type", StringType()),
        StructField("phase_number", LongType()),
        StructField("phase_name", StringType()),
        StructField("initiated_count", LongType()),
        StructField("completed_count", LongType()),
        StructField("timeout_rate", DoubleType()),
        StructField("median_time_ms", LongType()),
        StructField("report_date", DateType()),
        StructField("computed_at", TimestampType()),
        StructField("date", DateType()),
    ])
    phase_names = ["syn_sent", "syn_ack", "ack", "client_hello",
                   "server_hello", "key_exchange", "finished"]
    rows = []
    for d in DATES:
        for ht in HANDSHAKE_TYPES:
            for pn, pname in enumerate(phase_names, 1):
                initiated = random.randint(50000, 500000)
                completed = int(initiated * random.uniform(0.85, 0.999))
                rows.append((
                    ht, pn, pname, initiated, completed,
                    round(1.0 - completed / initiated, 4),
                    random.randint(1, 500), d, rand_ts(d), d,
                ))
    return schema, rows


def gen_ab_routing_experiment_engine():
    schema = StructType([
        StructField("experiment_id", StringType()),
        StructField("route_variant", StringType()),
        StructField("sample_size", LongType()),
        StructField("latency_improvement_pct", DoubleType()),
        StructField("throughput_uplift_pct", DoubleType()),
        StructField("p_value", DoubleType()),
        StructField("is_significant", BooleanType()),
        StructField("computed_at", TimestampType()),
        StructField("date", DateType()),
    ])
    variants = ["control", "shortest-path", "least-congestion",
                "geo-optimized", "cost-optimized"]
    rows = []
    eid = 1
    for d in DATES:
        for _ in range(30):
            exp_id = f"exp-{eid:05d}"
            for var in variants:
                p_val = round(random.uniform(0.001, 0.5), 4)
                rows.append((
                    exp_id, var,
                    random.randint(1000, 100000),
                    round(random.uniform(-5.0, 25.0), 2),
                    round(random.uniform(-3.0, 15.0), 2),
                    p_val, p_val < 0.05, rand_ts(d), d,
                ))
            eid += 1
    return schema, rows


def gen_endpoint_activity_scoring():
    schema = StructType([
        StructField("endpoint_id", StringType()),
        StructField("activity_score", DoubleType()),
        StructField("recency_score", DoubleType()),
        StructField("frequency_score", DoubleType()),
        StructField("bandwidth_score", DoubleType()),
        StructField("protocol_diversity_score", DoubleType()),
        StructField("tier", StringType()),
        StructField("scored_at", TimestampType()),
        StructField("date", DateType()),
    ])
    tiers = ["platinum", "gold", "silver", "bronze", "inactive"]
    rows = []
    eid = 1
    for d in DATES:
        for _ in range(500):
            activity = round(random.uniform(0.0, 100.0), 2)
            rows.append((
                f"ep-{eid:06d}",
                activity,
                round(random.uniform(0.0, 100.0), 2),
                round(random.uniform(0.0, 100.0), 2),
                round(random.uniform(0.0, 100.0), 2),
                round(random.uniform(0.0, 100.0), 2),
                tiers[min(int(activity / 25), 4) if activity < 100 else 0],
                rand_ts(d), d,
            ))
            eid += 1
    return schema, rows


def gen_device_onboarding_monitor():
    schema = StructType([
        StructField("batch_date", DateType()),
        StructField("phase_name", StringType()),
        StructField("phase_order", LongType()),
        StructField("devices_reached", LongType()),
        StructField("completion_rate", DoubleType()),
        StructField("median_provision_time_sec", LongType()),
        StructField("rejection_rate", DoubleType()),
        StructField("computed_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    for d in DATES:
        for batch in range(20):
            base_devices = random.randint(50, 500)
            for order, phase in enumerate(ONBOARDING_PHASES, 1):
                devices = int(base_devices * (1.0 - 0.08 * order) + random.randint(-5, 5))
                devices = max(1, devices)
                rows.append((
                    d, phase, order, devices,
                    round(random.uniform(0.7, 1.0), 3),
                    random.randint(10, 600),
                    round(random.uniform(0.0, 0.15), 3),
                    rand_ts(d), d,
                ))
    return schema, rows


def gen_traffic_class_segments():
    schema = StructType([
        StructField("endpoint_id", StringType()),
        StructField("traffic_class", StringType()),
        StructField("previous_class", StringType()),
        StructField("days_in_class", LongType()),
        StructField("flow_count_30d", LongType()),
        StructField("protocols_used_30d", LongType()),
        StructField("last_active_at", TimestampType()),
        StructField("classified_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    eid = 1
    for d in DATES:
        for _ in range(150):
            tc = random.choice(TRAFFIC_CLASSES)
            prev = random.choice([c for c in TRAFFIC_CLASSES if c != tc])
            ts = rand_ts(d)
            rows.append((
                f"ep-{eid:06d}", tc, prev,
                random.randint(1, 90),
                random.randint(100, 50000),
                random.randint(1, len(PROTOCOLS)),
                ts - timedelta(hours=random.randint(0, 48)),
                ts, d,
            ))
            eid += 1
    return schema, rows


def gen_dhcp_lease_sync():
    schema = StructType([
        StructField("lease_id", LongType()),
        StructField("ip_address", StringType()),
        StructField("mac_address", StringType()),
        StructField("hostname", StringType()),
        StructField("pool_name", StringType()),
        StructField("lease_state", StringType()),
        StructField("lease_start", TimestampType()),
        StructField("lease_expiry", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    lid = 1
    for d in DATES:
        for _ in range(500):
            ts = rand_ts(d)
            rows.append((
                lid, rand_ip(), rand_mac(),
                random.choice(HOSTNAMES),
                random.choice(POOL_NAMES),
                random.choice(LEASE_STATES),
                ts, ts + timedelta(hours=random.choice([1, 4, 8, 24, 168])),
                d,
            ))
            lid += 1
    return schema, rows


def gen_http_access_log_ingest():
    schema = StructType([
        StructField("request_id", StringType()),
        StructField("client_ip", StringType()),
        StructField("request_path", StringType()),
        StructField("method", StringType()),
        StructField("status_code", LongType()),
        StructField("user_agent", StringType()),
        StructField("response_time_ms", LongType()),
        StructField("request_time", TimestampType()),
        StructField("date", DateType()),
    ])
    status_codes = [200, 200, 200, 200, 201, 204, 301, 304, 400, 401, 403, 404, 500, 502, 503]
    rows = []
    rid = 1
    for d in DATES:
        for _ in range(200):
            rows.append((
                f"req-{rid:08d}", rand_ip(),
                random.choice(REQUEST_PATHS),
                random.choice(METHODS),
                random.choice(status_codes),
                random.choice(USER_AGENTS),
                random.randint(1, 5000),
                rand_ts(d), d,
            ))
            rid += 1
    return schema, rows


def gen_traffic_attribution_model():
    schema = StructType([
        StructField("attribution_id", StringType()),
        StructField("flow_id", StringType()),
        StructField("interface", StringType()),
        StructField("hop_position", StringType()),
        StructField("attribution_weight", DoubleType()),
        StructField("bandwidth_attributed_mbps", DoubleType()),
        StructField("model_type", StringType()),
        StructField("computed_at", TimestampType()),
        StructField("date", DateType()),
    ])
    hop_positions = ["ingress", "core-1", "core-2", "egress"]
    rows = []
    aid = 1
    for d in DATES:
        for _ in range(175):
            rows.append((
                f"attr-{aid:07d}", f"flow-{random.randint(1,99999):08d}",
                random.choice(INTERFACES),
                random.choice(hop_positions),
                round(random.uniform(0.0, 1.0), 4),
                round(random.uniform(0.1, 1000.0), 2),
                random.choice(MODEL_TYPES),
                rand_ts(d), d,
            ))
            aid += 1
    return schema, rows


def gen_threat_scoring_pipeline():
    schema = StructType([
        StructField("source_ip", StringType()),
        StructField("threat_score", DoubleType()),
        StructField("risk_bucket", StringType()),
        StructField("anomaly_score", DoubleType()),
        StructField("reputation_score", DoubleType()),
        StructField("suspicious_connections", LongType()),
        StructField("is_blocked", BooleanType()),
        StructField("scored_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    for d in DATES:
        for _ in range(500):
            threat = round(random.uniform(0.0, 100.0), 2)
            bucket = (
                "low" if threat < 25 else
                "medium" if threat < 50 else
                "high" if threat < 75 else "critical"
            )
            rows.append((
                rand_ip(), threat, bucket,
                round(random.uniform(0.0, 100.0), 2),
                round(random.uniform(0.0, 100.0), 2),
                random.randint(0, 500),
                threat > 80,
                rand_ts(d), d,
            ))
    return schema, rows


def gen_peering_roi_calculator():
    schema = StructType([
        StructField("peer_id", StringType()),
        StructField("peer_name", StringType()),
        StructField("interface", StringType()),
        StructField("transit_cost", DoubleType()),
        StructField("bandwidth_value", DoubleType()),
        StructField("roi_pct", DoubleType()),
        StructField("prefixes_exchanged", LongType()),
        StructField("report_date", DateType()),
        StructField("date", DateType()),
    ])
    rows = []
    pid = 1
    for d in DATES:
        for pname in PEER_NAMES:
            for iface in random.sample(INTERFACES, 3):
                transit = round(random.uniform(500.0, 50000.0), 2)
                bw_val = round(transit * random.uniform(0.5, 3.0), 2)
                rows.append((
                    f"peer-{pid:04d}", pname, iface,
                    transit, bw_val,
                    round((bw_val - transit) / transit * 100, 2),
                    random.randint(50, 5000),
                    d, d,
                ))
                pid += 1
    return schema, rows


def gen_capacity_planning_forecast():
    schema = StructType([
        StructField("forecast_id", StringType()),
        StructField("period", StringType()),
        StructField("current_utilization_pct", DoubleType()),
        StructField("projected_utilization_pct", DoubleType()),
        StructField("saturation_probability", DoubleType()),
        StructField("links_at_risk", LongType()),
        StructField("recommended_upgrade_gbps", DoubleType()),
        StructField("forecast_date", DateType()),
        StructField("date", DateType()),
    ])
    periods = ["2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1", "2027-Q2"]
    rows = []
    fid = 1
    for d in DATES:
        for period in periods:
            for _ in range(25):
                current = round(random.uniform(20.0, 90.0), 2)
                projected = round(current + random.uniform(2.0, 30.0), 2)
                rows.append((
                    f"fc-{fid:06d}", period, current,
                    min(projected, 100.0),
                    round(random.uniform(0.0, 1.0), 3),
                    random.randint(0, 20),
                    round(random.uniform(0.0, 400.0), 1),
                    d, d,
                ))
                fid += 1
    return schema, rows


def gen_mac_address_enrichment():
    schema = StructType([
        StructField("mac_address", StringType()),
        StructField("ip_address", StringType()),
        StructField("total_flows", LongType()),
        StructField("unique_destinations", LongType()),
        StructField("last_seen_interface", StringType()),
        StructField("vendor_name", StringType()),
        StructField("days_since_last_seen", LongType()),
        StructField("enriched_at", TimestampType()),
        StructField("date", DateType()),
    ])
    vendors = ["Cisco Systems", "Juniper Networks", "Arista Networks",
               "Hewlett Packard", "Dell Technologies", "Intel Corp",
               "Ubiquiti Inc", "Palo Alto Networks", "Fortinet Inc",
               "Ruckus Wireless"]
    rows = []
    for d in DATES:
        for _ in range(175):
            rows.append((
                rand_mac(), rand_ip(),
                random.randint(10, 100000),
                random.randint(1, 500),
                random.choice(INTERFACES),
                random.choice(vendors),
                random.randint(0, 90),
                rand_ts(d), d,
            ))
    return schema, rows


def gen_cdn_cost_reconciler():
    schema = StructType([
        StructField("cdn_provider", StringType()),
        StructField("region", StringType()),
        StructField("reported_bandwidth_gb", DoubleType()),
        StructField("actual_bandwidth_gb", DoubleType()),
        StructField("discrepancy_pct", DoubleType()),
        StructField("cache_hit_ratio", DoubleType()),
        StructField("requests_total", LongType()),
        StructField("reconciled_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    for d in DATES:
        for provider in CDN_PROVIDERS:
            for region in CDN_REGIONS:
                for _ in range(5):
                    reported = round(random.uniform(100.0, 50000.0), 2)
                    actual = round(reported * random.uniform(0.85, 1.15), 2)
                    rows.append((
                        provider, region, reported, actual,
                        round((actual - reported) / reported * 100, 2),
                        round(random.uniform(0.5, 0.99), 4),
                        random.randint(10000, 10000000),
                        rand_ts(d), d,
                    ))
    return schema, rows


def gen_weekly_network_digest():
    schema = StructType([
        StructField("digest_id", StringType()),
        StructField("week_start", DateType()),
        StructField("total_bandwidth_tb", DoubleType()),
        StructField("total_incidents", LongType()),
        StructField("uptime_pct", DoubleType()),
        StructField("top_protocol", StringType()),
        StructField("new_endpoints", LongType()),
        StructField("generated_at", TimestampType()),
        StructField("date", DateType()),
    ])
    rows = []
    did = 1
    for d in DATES:
        for _ in range(125):
            rows.append((
                f"digest-{did:05d}",
                d - timedelta(days=d.weekday()),
                round(random.uniform(10.0, 500.0), 2),
                random.randint(0, 150),
                round(random.uniform(99.0, 100.0), 4),
                random.choice(PROTOCOLS),
                random.randint(0, 200),
                rand_ts(d), d,
            ))
            did += 1
    return schema, rows


def gen_unified_network_assessment():
    schema = StructType([
        StructField("ip_address", StringType()),
        StructField("hostname", StringType()),
        StructField("mac_address", StringType()),
        StructField("network_zone", StringType()),
        StructField("total_flows", LongType()),
        StructField("total_bytes", LongType()),
        StructField("avg_bytes_per_flow", DoubleType()),
        StructField("unique_destinations", LongType()),
        StructField("protocol_count", LongType()),
        StructField("protocols_csv", StringType()),
        StructField("threat_score", DoubleType()),
        StructField("risk_bucket", StringType()),
        StructField("anomaly_score", DoubleType()),
        StructField("reputation_score", DoubleType()),
        StructField("is_blocked", BooleanType()),
        StructField("critical_event_count", LongType()),
        StructField("affected_facilities", LongType()),
        StructField("syslog_severity_score", DoubleType()),
        StructField("composite_health_score", DoubleType()),
        StructField("assessment_tier", StringType()),
        StructField("requires_action", BooleanType()),
        StructField("rank_in_risk_bucket", IntegerType()),
        StructField("global_percentile", DoubleType()),
        StructField("traffic_quartile", IntegerType()),
        StructField("activity_score", DoubleType()),
        StructField("activity_tier", StringType()),
        StructField("assessed_at", TimestampType()),
        StructField("date", DateType()),
    ])
    tiers = ["healthy", "moderate", "degraded", "critical", "severe"]
    activity_tiers = ["platinum", "gold", "silver", "bronze", "unknown"]
    rows = []
    for d in DATES:
        for _ in range(150):
            health = round(random.uniform(0.0, 100.0), 2)
            tier_idx = min(int((100 - health) / 20), 4)
            threat = round(random.uniform(0.0, 100.0), 2)
            protos = random.sample(PROTOCOLS, random.randint(1, 4))
            rows.append((
                rand_ip(),
                random.choice(HOSTNAMES),
                rand_mac(),
                random.choice(POOL_NAMES),
                random.randint(1, 10000),
                random.randint(1000, 1500000000),
                round(random.uniform(100.0, 500000.0), 2),
                random.randint(1, 200),
                len(protos),
                ",".join(protos),
                threat,
                random.choice(RISK_BUCKETS),
                round(random.uniform(0.0, 100.0), 2),
                round(random.uniform(0.0, 1.0), 4),
                threat > 80,
                random.randint(0, 50),
                random.randint(0, 8),
                round(random.uniform(0.0, 200.0), 2),
                health,
                tiers[tier_idx],
                health < 30 or threat > 80,
                random.randint(1, 100),
                round(random.uniform(0.0, 1.0), 4),
                random.randint(1, 4),
                round(random.uniform(0.0, 100.0), 2),
                random.choice(activity_tiers),
                rand_ts(d),
                d,
            ))
    return schema, rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

NAMESPACE_TABLES = {
    "dagger": {
        "PortScanCollector": gen_switch_port_collector,
        "RouteTableRecon": gen_bgp_route_sync,
        "FlowInterceptor": gen_netflow_capture,
        "DeviceFingerprinter": gen_device_fingerprint_enrichment,
        "BandwidthAnalyzer": gen_bandwidth_billing_aggregator,
        "LinkAnomalyDetector": gen_link_failure_prediction,
        "BandwidthAuditReconciler": gen_bandwidth_cost_reconciliation,
        "NocThreatSnapshot": gen_noc_dashboard_snapshot,
        "NetworkThreatAssessment": gen_unified_network_assessment,
    },
    "prism": {
        "DeepPacketInspector": gen_packet_inspection_enrichment,
        "ProtocolAnalyzer": gen_protocol_adoption_tracker,
        "HandshakeAnalyzer": gen_handshake_completion_analysis,
        "RoutingExperimentEngine": gen_ab_routing_experiment_engine,
        "EndpointRiskScorer": gen_endpoint_activity_scoring,
        "ProvisioningAuditor": gen_device_onboarding_monitor,
        "TrafficClassifier": gen_traffic_class_segments,
    },
    "vault": {
        "DhcpLeaseRecon": gen_dhcp_lease_sync,
        "AccessLogCollector": gen_http_access_log_ingest,
        "TrafficAttributionAnalyzer": gen_traffic_attribution_model,
        "ThreatHunterScorer": gen_threat_scoring_pipeline,
        "MacIntelEnrichment": gen_mac_address_enrichment,
        "CdnAuditReconciler": gen_cdn_cost_reconciler,
        "PeeringIntelCalculator": gen_peering_roi_calculator,
        "CapacityThreatForecast": gen_capacity_planning_forecast,
        "WeeklyThreatDigest": gen_weekly_network_digest,
    },
    "oasis": {
        "DnsIntelSync": gen_dns_record_sync,
        "SyslogCollector": gen_syslog_event_stream,
        "IncidentForensicsRollup": gen_incident_analytics_rollup,
    },
}


def main():
    if not wait_for_catalog():
        sys.exit(1)

    spark = create_spark_session()

    total_tables = sum(len(tables) for tables in NAMESPACE_TABLES.values())
    print(f"Seeding {total_tables} Iceberg tables across {len(NAMESPACE_TABLES)} namespaces...")
    total_rows = 0
    for namespace, tables in NAMESPACE_TABLES.items():
        print(f"\nNamespace: {namespace} ({len(tables)} tables)")
        for table_name, gen_fn in tables.items():
            try:
                schema, rows = gen_fn()
                seed_table(spark, namespace, table_name, schema, rows)
                total_rows += len(rows)
            except Exception as e:
                print(f"  ERROR seeding {namespace}.{table_name}: {e}")
                raise

    print(f"\nData seeding complete! Total rows: {total_rows}")
    spark.stop()
    sys.exit(0)


if __name__ == "__main__":
    main()
