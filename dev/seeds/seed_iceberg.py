"""Seed Iceberg REST catalog with table schemas for dev environment."""

import json
import sys
import time
import urllib.request
import urllib.error

CATALOG_URL = "http://iceberg-rest:8181"
NAMESPACE = "dagger"

TABLES = {
    "BgpRouteSync": [
        {"id": 1, "name": "route_id", "type": "long", "required": False},
        {"id": 2, "name": "prefix", "type": "string", "required": False},
        {"id": 3, "name": "next_hop", "type": "string", "required": False},
        {"id": 4, "name": "as_path", "type": "string", "required": False},
        {"id": 5, "name": "origin", "type": "string", "required": False},
        {"id": 6, "name": "status", "type": "string", "required": False},
        {"id": 7, "name": "peer_id", "type": "long", "required": False},
        {"id": 8, "name": "synced_at", "type": "timestamp", "required": False},
    ],
    "SyslogEventStream": [
        {"id": 1, "name": "event_id", "type": "long", "required": False},
        {"id": 2, "name": "source_host", "type": "string", "required": False},
        {"id": 3, "name": "facility", "type": "string", "required": False},
        {"id": 4, "name": "severity", "type": "string", "required": False},
        {"id": 5, "name": "message", "type": "string", "required": False},
        {"id": 6, "name": "priority", "type": "string", "required": False},
        {"id": 7, "name": "event_time", "type": "timestamp", "required": False},
        {"id": 8, "name": "received_at", "type": "timestamp", "required": False},
    ],
    "BandwidthBillingAggregator": [
        {"id": 1, "name": "invoice_id", "type": "string", "required": False},
        {"id": 2, "name": "circuit_id", "type": "string", "required": False},
        {"id": 3, "name": "subscription_id", "type": "string", "required": False},
        {"id": 4, "name": "bandwidth_allocated_mbps", "type": "double", "required": False},
        {"id": 5, "name": "bandwidth_used_mbps", "type": "double", "required": False},
        {"id": 6, "name": "billing_tier", "type": "string", "required": False},
        {"id": 7, "name": "status", "type": "string", "required": False},
        {"id": 8, "name": "period_start", "type": "timestamp", "required": False},
        {"id": 9, "name": "period_end", "type": "timestamp", "required": False},
        {"id": 10, "name": "created_at", "type": "timestamp", "required": False},
    ],
    "NetflowCapture": [
        {"id": 1, "name": "flow_id", "type": "string", "required": False},
        {"id": 2, "name": "src_ip", "type": "string", "required": False},
        {"id": 3, "name": "dst_ip", "type": "string", "required": False},
        {"id": 4, "name": "capture_time", "type": "timestamp", "required": False},
        {"id": 5, "name": "session_id", "type": "string", "required": False},
        {"id": 6, "name": "protocol", "type": "string", "required": False},
        {"id": 7, "name": "bytes_transferred", "type": "long", "required": False},
        {"id": 8, "name": "collected_at", "type": "timestamp", "required": False},
    ],
    "DnsRecordSync": [
        {"id": 1, "name": "record_id", "type": "string", "required": False},
        {"id": 2, "name": "zone_name", "type": "string", "required": False},
        {"id": 3, "name": "record_type", "type": "string", "required": False},
        {"id": 4, "name": "ttl", "type": "long", "required": False},
        {"id": 5, "name": "record_value", "type": "string", "required": False},
        {"id": 6, "name": "status", "type": "string", "required": False},
        {"id": 7, "name": "created_date", "type": "date", "required": False},
        {"id": 8, "name": "last_modified_date", "type": "timestamp", "required": False},
    ],
    "SwitchPortCollector": [
        {"id": 1, "name": "switch_id", "type": "long", "required": False},
        {"id": 2, "name": "port_number", "type": "string", "required": False},
        {"id": 3, "name": "mac_address", "type": "string", "required": False},
        {"id": 4, "name": "collected_at", "type": "timestamp", "required": False},
        {"id": 5, "name": "last_state_change", "type": "timestamp", "required": False},
        {"id": 6, "name": "is_active", "type": "boolean", "required": False},
        {"id": 7, "name": "port_speed", "type": "string", "required": False},
        {"id": 8, "name": "vlan_id", "type": "long", "required": False},
    ],
    "DeviceFingerprintEnrichment": [
        {"id": 1, "name": "device_id", "type": "string", "required": False},
        {"id": 2, "name": "mac_address", "type": "string", "required": False},
        {"id": 3, "name": "hostname", "type": "string", "required": False},
        {"id": 4, "name": "open_ports", "type": "long", "required": False},
        {"id": 5, "name": "os_fingerprint", "type": "string", "required": False},
        {"id": 6, "name": "device_class", "type": "string", "required": False},
        {"id": 7, "name": "switch_port", "type": "string", "required": False},
        {"id": 8, "name": "enriched_at", "type": "timestamp", "required": False},
    ],
    "BandwidthCostReconciliation": [
        {"id": 1, "name": "reconciliation_id", "type": "string", "required": False},
        {"id": 2, "name": "circuit_id", "type": "string", "required": False},
        {"id": 3, "name": "invoice_id", "type": "string", "required": False},
        {"id": 4, "name": "metered_bytes", "type": "double", "required": False},
        {"id": 5, "name": "billed_bytes", "type": "double", "required": False},
        {"id": 6, "name": "variance_pct", "type": "double", "required": False},
        {"id": 7, "name": "status", "type": "string", "required": False},
        {"id": 8, "name": "reconciled_at", "type": "timestamp", "required": False},
    ],
    "LinkFailurePrediction": [
        {"id": 1, "name": "link_id", "type": "string", "required": False},
        {"id": 2, "name": "hours_since_last_flap", "type": "long", "required": False},
        {"id": 3, "name": "avg_error_rate", "type": "double", "required": False},
        {"id": 4, "name": "crc_errors_30d", "type": "long", "required": False},
        {"id": 5, "name": "packet_loss_events_90d", "type": "long", "required": False},
        {"id": 6, "name": "failure_probability", "type": "double", "required": False},
        {"id": 7, "name": "health_score", "type": "double", "required": False},
        {"id": 8, "name": "scored_at", "type": "timestamp", "required": False},
    ],
    "IncidentAnalyticsRollup": [
        {"id": 1, "name": "period", "type": "string", "required": False},
        {"id": 2, "name": "total_incidents", "type": "long", "required": False},
        {"id": 3, "name": "avg_resolution_minutes", "type": "double", "required": False},
        {"id": 4, "name": "severity_score", "type": "double", "required": False},
        {"id": 5, "name": "responder_id", "type": "string", "required": False},
        {"id": 6, "name": "sla_met_pct", "type": "double", "required": False},
        {"id": 7, "name": "escalation_rate", "type": "double", "required": False},
        {"id": 8, "name": "computed_at", "type": "timestamp", "required": False},
    ],
    "NocDashboardSnapshot": [
        {"id": 1, "name": "snapshot_date", "type": "date", "required": False},
        {"id": 2, "name": "total_bandwidth_gbps", "type": "double", "required": False},
        {"id": 3, "name": "peak_throughput_gbps", "type": "double", "required": False},
        {"id": 4, "name": "active_endpoints", "type": "long", "required": False},
        {"id": 5, "name": "link_failure_rate", "type": "double", "required": False},
        {"id": 6, "name": "avg_health_score", "type": "double", "required": False},
        {"id": 7, "name": "avg_latency_ms", "type": "double", "required": False},
        {"id": 8, "name": "generated_at", "type": "timestamp", "required": False},
    ],
    "PacketInspectionEnrichment": [
        {"id": 1, "name": "packet_id", "type": "string", "required": False},
        {"id": 2, "name": "src_ip", "type": "string", "required": False},
        {"id": 3, "name": "protocol", "type": "string", "required": False},
        {"id": 4, "name": "capture_time", "type": "timestamp", "required": False},
        {"id": 5, "name": "session_id", "type": "string", "required": False},
        {"id": 6, "name": "application_layer", "type": "string", "required": False},
        {"id": 7, "name": "port_speed", "type": "string", "required": False},
        {"id": 8, "name": "vlan_id", "type": "long", "required": False},
        {"id": 9, "name": "first_seen_date", "type": "date", "required": False},
        {"id": 10, "name": "enriched_at", "type": "timestamp", "required": False},
    ],
    "ProtocolAdoptionTracker": [
        {"id": 1, "name": "protocol_name", "type": "string", "required": False},
        {"id": 2, "name": "report_date", "type": "date", "required": False},
        {"id": 3, "name": "unique_endpoints", "type": "long", "required": False},
        {"id": 4, "name": "first_seen_count", "type": "long", "required": False},
        {"id": 5, "name": "daily_active", "type": "long", "required": False},
        {"id": 6, "name": "weekly_active", "type": "long", "required": False},
        {"id": 7, "name": "adoption_rate", "type": "double", "required": False},
        {"id": 8, "name": "computed_at", "type": "timestamp", "required": False},
    ],
    "HandshakeCompletionAnalysis": [
        {"id": 1, "name": "handshake_type", "type": "string", "required": False},
        {"id": 2, "name": "phase_number", "type": "long", "required": False},
        {"id": 3, "name": "phase_name", "type": "string", "required": False},
        {"id": 4, "name": "initiated_count", "type": "long", "required": False},
        {"id": 5, "name": "completed_count", "type": "long", "required": False},
        {"id": 6, "name": "timeout_rate", "type": "double", "required": False},
        {"id": 7, "name": "median_time_ms", "type": "long", "required": False},
        {"id": 8, "name": "report_date", "type": "date", "required": False},
        {"id": 9, "name": "computed_at", "type": "timestamp", "required": False},
    ],
    "AbRoutingExperimentEngine": [
        {"id": 1, "name": "experiment_id", "type": "string", "required": False},
        {"id": 2, "name": "route_variant", "type": "string", "required": False},
        {"id": 3, "name": "sample_size", "type": "long", "required": False},
        {"id": 4, "name": "latency_improvement_pct", "type": "double", "required": False},
        {"id": 5, "name": "throughput_uplift_pct", "type": "double", "required": False},
        {"id": 6, "name": "p_value", "type": "double", "required": False},
        {"id": 7, "name": "is_significant", "type": "boolean", "required": False},
        {"id": 8, "name": "computed_at", "type": "timestamp", "required": False},
    ],
    "EndpointActivityScoring": [
        {"id": 1, "name": "endpoint_id", "type": "string", "required": False},
        {"id": 2, "name": "activity_score", "type": "double", "required": False},
        {"id": 3, "name": "recency_score", "type": "double", "required": False},
        {"id": 4, "name": "frequency_score", "type": "double", "required": False},
        {"id": 5, "name": "bandwidth_score", "type": "double", "required": False},
        {"id": 6, "name": "protocol_diversity_score", "type": "double", "required": False},
        {"id": 7, "name": "tier", "type": "string", "required": False},
        {"id": 8, "name": "scored_at", "type": "timestamp", "required": False},
    ],
    "DeviceOnboardingMonitor": [
        {"id": 1, "name": "batch_date", "type": "date", "required": False},
        {"id": 2, "name": "phase_name", "type": "string", "required": False},
        {"id": 3, "name": "phase_order", "type": "long", "required": False},
        {"id": 4, "name": "devices_reached", "type": "long", "required": False},
        {"id": 5, "name": "completion_rate", "type": "double", "required": False},
        {"id": 6, "name": "median_provision_time_sec", "type": "long", "required": False},
        {"id": 7, "name": "rejection_rate", "type": "double", "required": False},
        {"id": 8, "name": "computed_at", "type": "timestamp", "required": False},
    ],
    "TrafficClassSegments": [
        {"id": 1, "name": "endpoint_id", "type": "string", "required": False},
        {"id": 2, "name": "traffic_class", "type": "string", "required": False},
        {"id": 3, "name": "previous_class", "type": "string", "required": False},
        {"id": 4, "name": "days_in_class", "type": "long", "required": False},
        {"id": 5, "name": "flow_count_30d", "type": "long", "required": False},
        {"id": 6, "name": "protocols_used_30d", "type": "long", "required": False},
        {"id": 7, "name": "last_active_at", "type": "timestamp", "required": False},
        {"id": 8, "name": "classified_at", "type": "timestamp", "required": False},
    ],
    "DhcpLeaseSync": [
        {"id": 1, "name": "lease_id", "type": "long", "required": False},
        {"id": 2, "name": "ip_address", "type": "string", "required": False},
        {"id": 3, "name": "mac_address", "type": "string", "required": False},
        {"id": 4, "name": "hostname", "type": "string", "required": False},
        {"id": 5, "name": "pool_name", "type": "string", "required": False},
        {"id": 6, "name": "lease_state", "type": "string", "required": False},
        {"id": 7, "name": "lease_start", "type": "timestamp", "required": False},
        {"id": 8, "name": "lease_expiry", "type": "timestamp", "required": False},
    ],
    "HttpAccessLogIngest": [
        {"id": 1, "name": "request_id", "type": "string", "required": False},
        {"id": 2, "name": "client_ip", "type": "string", "required": False},
        {"id": 3, "name": "request_path", "type": "string", "required": False},
        {"id": 4, "name": "method", "type": "string", "required": False},
        {"id": 5, "name": "status_code", "type": "long", "required": False},
        {"id": 6, "name": "user_agent", "type": "string", "required": False},
        {"id": 7, "name": "response_time_ms", "type": "long", "required": False},
        {"id": 8, "name": "request_time", "type": "timestamp", "required": False},
    ],
    "TrafficAttributionModel": [
        {"id": 1, "name": "attribution_id", "type": "string", "required": False},
        {"id": 2, "name": "flow_id", "type": "string", "required": False},
        {"id": 3, "name": "interface", "type": "string", "required": False},
        {"id": 4, "name": "hop_position", "type": "string", "required": False},
        {"id": 5, "name": "attribution_weight", "type": "double", "required": False},
        {"id": 6, "name": "bandwidth_attributed_mbps", "type": "double", "required": False},
        {"id": 7, "name": "model_type", "type": "string", "required": False},
        {"id": 8, "name": "computed_at", "type": "timestamp", "required": False},
    ],
    "ThreatScoringPipeline": [
        {"id": 1, "name": "source_ip", "type": "string", "required": False},
        {"id": 2, "name": "threat_score", "type": "double", "required": False},
        {"id": 3, "name": "risk_bucket", "type": "string", "required": False},
        {"id": 4, "name": "anomaly_score", "type": "double", "required": False},
        {"id": 5, "name": "reputation_score", "type": "double", "required": False},
        {"id": 6, "name": "suspicious_connections", "type": "long", "required": False},
        {"id": 7, "name": "is_blocked", "type": "boolean", "required": False},
        {"id": 8, "name": "scored_at", "type": "timestamp", "required": False},
    ],
    "PeeringRoiCalculator": [
        {"id": 1, "name": "peer_id", "type": "string", "required": False},
        {"id": 2, "name": "peer_name", "type": "string", "required": False},
        {"id": 3, "name": "interface", "type": "string", "required": False},
        {"id": 4, "name": "transit_cost", "type": "double", "required": False},
        {"id": 5, "name": "bandwidth_value", "type": "double", "required": False},
        {"id": 6, "name": "roi_pct", "type": "double", "required": False},
        {"id": 7, "name": "prefixes_exchanged", "type": "long", "required": False},
        {"id": 8, "name": "report_date", "type": "date", "required": False},
    ],
    "CapacityPlanningForecast": [
        {"id": 1, "name": "forecast_id", "type": "string", "required": False},
        {"id": 2, "name": "period", "type": "string", "required": False},
        {"id": 3, "name": "current_utilization_pct", "type": "double", "required": False},
        {"id": 4, "name": "projected_utilization_pct", "type": "double", "required": False},
        {"id": 5, "name": "saturation_probability", "type": "double", "required": False},
        {"id": 6, "name": "links_at_risk", "type": "long", "required": False},
        {"id": 7, "name": "recommended_upgrade_gbps", "type": "double", "required": False},
        {"id": 8, "name": "forecast_date", "type": "date", "required": False},
    ],
    "MacAddressEnrichment": [
        {"id": 1, "name": "mac_address", "type": "string", "required": False},
        {"id": 2, "name": "ip_address", "type": "string", "required": False},
        {"id": 3, "name": "total_flows", "type": "long", "required": False},
        {"id": 4, "name": "unique_destinations", "type": "long", "required": False},
        {"id": 5, "name": "last_seen_interface", "type": "string", "required": False},
        {"id": 6, "name": "vendor_name", "type": "string", "required": False},
        {"id": 7, "name": "days_since_last_seen", "type": "long", "required": False},
        {"id": 8, "name": "enriched_at", "type": "timestamp", "required": False},
    ],
    "CdnCostReconciler": [
        {"id": 1, "name": "cdn_provider", "type": "string", "required": False},
        {"id": 2, "name": "region", "type": "string", "required": False},
        {"id": 3, "name": "reported_bandwidth_gb", "type": "double", "required": False},
        {"id": 4, "name": "actual_bandwidth_gb", "type": "double", "required": False},
        {"id": 5, "name": "discrepancy_pct", "type": "double", "required": False},
        {"id": 6, "name": "cache_hit_ratio", "type": "double", "required": False},
        {"id": 7, "name": "requests_total", "type": "long", "required": False},
        {"id": 8, "name": "reconciled_at", "type": "timestamp", "required": False},
    ],
    "WeeklyNetworkDigest": [
        {"id": 1, "name": "digest_id", "type": "string", "required": False},
        {"id": 2, "name": "week_start", "type": "date", "required": False},
        {"id": 3, "name": "total_bandwidth_tb", "type": "double", "required": False},
        {"id": 4, "name": "total_incidents", "type": "long", "required": False},
        {"id": 5, "name": "uptime_pct", "type": "double", "required": False},
        {"id": 6, "name": "top_protocol", "type": "string", "required": False},
        {"id": 7, "name": "new_endpoints", "type": "long", "required": False},
        {"id": 8, "name": "generated_at", "type": "timestamp", "required": False},
    ],
}


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


def api_request(method, path, body=None):
    """Make a request to the Iceberg REST API."""
    url = f"{CATALOG_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        return e.code, body_text


def create_namespace():
    """Create the dagger namespace."""
    status, resp = api_request("POST", "/v1/namespaces", {
        "namespace": [NAMESPACE],
    })
    if status == 200:
        print(f"Created namespace: {NAMESPACE}")
    elif status == 409:
        print(f"Namespace already exists: {NAMESPACE}")
    else:
        print(f"Namespace creation returned {status}: {resp}")


def create_table(table_name, fields):
    """Create an Iceberg table with the given schema."""
    body = {
        "name": table_name,
        "schema": {
            "type": "struct",
            "schema-id": 0,
            "fields": fields,
        },
    }
    status, resp = api_request(
        "POST", f"/v1/namespaces/{NAMESPACE}/tables", body
    )
    if status == 200:
        print(f"  Created table: {NAMESPACE}.{table_name} ({len(fields)} fields)")
    elif status == 409:
        print(f"  Table already exists: {NAMESPACE}.{table_name}")
    else:
        print(f"  Table {table_name} creation returned {status}: {resp}")


def main():
    if not wait_for_catalog():
        sys.exit(1)

    create_namespace()

    print(f"Creating {len(TABLES)} tables...")
    for table_name, fields in TABLES.items():
        create_table(table_name, fields)

    print("Iceberg catalog seeding complete!")


if __name__ == "__main__":
    main()
