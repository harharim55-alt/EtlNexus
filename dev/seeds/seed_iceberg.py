"""Seed Iceberg REST catalog with table schemas for dev environment."""

import json
import sys
import time
import urllib.request
import urllib.error

CATALOG_URL = "http://iceberg-rest:8181"
NAMESPACE = "dagger"

TABLES = {
    "shopify_sales_sync": [
        {"id": 1, "name": "order_id", "type": "long", "required": False},
        {"id": 2, "name": "customer_id", "type": "long", "required": False},
        {"id": 3, "name": "order_date", "type": "date", "required": False},
        {"id": 4, "name": "total_amount", "type": "double", "required": False},
        {"id": 5, "name": "currency", "type": "string", "required": False},
        {"id": 6, "name": "status", "type": "string", "required": False},
        {"id": 7, "name": "shop_id", "type": "long", "required": False},
        {"id": 8, "name": "created_at", "type": "timestamp", "required": False},
    ],
    "zendesk_tickets_stream": [
        {"id": 1, "name": "ticket_id", "type": "long", "required": False},
        {"id": 2, "name": "requester_id", "type": "long", "required": False},
        {"id": 3, "name": "assignee_id", "type": "long", "required": False},
        {"id": 4, "name": "subject", "type": "string", "required": False},
        {"id": 5, "name": "status", "type": "string", "required": False},
        {"id": 6, "name": "priority", "type": "string", "required": False},
        {"id": 7, "name": "created_at", "type": "timestamp", "required": False},
        {"id": 8, "name": "updated_at", "type": "timestamp", "required": False},
    ],
    "stripe_billing_aggregator": [
        {"id": 1, "name": "invoice_id", "type": "string", "required": False},
        {"id": 2, "name": "customer_id", "type": "string", "required": False},
        {"id": 3, "name": "subscription_id", "type": "string", "required": False},
        {"id": 4, "name": "amount_due", "type": "double", "required": False},
        {"id": 5, "name": "amount_paid", "type": "double", "required": False},
        {"id": 6, "name": "currency", "type": "string", "required": False},
        {"id": 7, "name": "status", "type": "string", "required": False},
        {"id": 8, "name": "period_start", "type": "timestamp", "required": False},
        {"id": 9, "name": "period_end", "type": "timestamp", "required": False},
        {"id": 10, "name": "created_at", "type": "timestamp", "required": False},
    ],
    "mixpanel_user_events": [
        {"id": 1, "name": "event_id", "type": "string", "required": False},
        {"id": 2, "name": "user_id", "type": "string", "required": False},
        {"id": 3, "name": "event_name", "type": "string", "required": False},
        {"id": 4, "name": "event_time", "type": "timestamp", "required": False},
        {"id": 5, "name": "session_id", "type": "string", "required": False},
        {"id": 6, "name": "platform", "type": "string", "required": False},
        {"id": 7, "name": "properties", "type": "string", "required": False},
        {"id": 8, "name": "created_at", "type": "timestamp", "required": False},
    ],
    "salesforce_crm_sync": [
        {"id": 1, "name": "account_id", "type": "string", "required": False},
        {"id": 2, "name": "account_name", "type": "string", "required": False},
        {"id": 3, "name": "industry", "type": "string", "required": False},
        {"id": 4, "name": "annual_revenue", "type": "double", "required": False},
        {"id": 5, "name": "owner_id", "type": "string", "required": False},
        {"id": 6, "name": "stage", "type": "string", "required": False},
        {"id": 7, "name": "created_date", "type": "date", "required": False},
        {"id": 8, "name": "last_modified_date", "type": "timestamp", "required": False},
    ],
    "postgres_production_db": [
        {"id": 1, "name": "user_id", "type": "long", "required": False},
        {"id": 2, "name": "email", "type": "string", "required": False},
        {"id": 3, "name": "username", "type": "string", "required": False},
        {"id": 4, "name": "created_at", "type": "timestamp", "required": False},
        {"id": 5, "name": "last_login_at", "type": "timestamp", "required": False},
        {"id": 6, "name": "is_active", "type": "boolean", "required": False},
        {"id": 7, "name": "plan_type", "type": "string", "required": False},
        {"id": 8, "name": "organization_id", "type": "long", "required": False},
    ],
    "customer_360_enrichment": [
        {"id": 1, "name": "customer_id", "type": "string", "required": False},
        {"id": 2, "name": "email", "type": "string", "required": False},
        {"id": 3, "name": "full_name", "type": "string", "required": False},
        {"id": 4, "name": "total_orders", "type": "long", "required": False},
        {"id": 5, "name": "lifetime_value", "type": "double", "required": False},
        {"id": 6, "name": "segment", "type": "string", "required": False},
        {"id": 7, "name": "account_id", "type": "string", "required": False},
        {"id": 8, "name": "enriched_at", "type": "timestamp", "required": False},
    ],
    "revenue_reconciliation": [
        {"id": 1, "name": "reconciliation_id", "type": "string", "required": False},
        {"id": 2, "name": "order_id", "type": "long", "required": False},
        {"id": 3, "name": "invoice_id", "type": "string", "required": False},
        {"id": 4, "name": "order_amount", "type": "double", "required": False},
        {"id": 5, "name": "billed_amount", "type": "double", "required": False},
        {"id": 6, "name": "variance", "type": "double", "required": False},
        {"id": 7, "name": "status", "type": "string", "required": False},
        {"id": 8, "name": "reconciled_at", "type": "timestamp", "required": False},
    ],
    "churn_prediction_features": [
        {"id": 1, "name": "customer_id", "type": "string", "required": False},
        {"id": 2, "name": "days_since_last_order", "type": "long", "required": False},
        {"id": 3, "name": "avg_order_value", "type": "double", "required": False},
        {"id": 4, "name": "login_frequency_30d", "type": "long", "required": False},
        {"id": 5, "name": "support_tickets_90d", "type": "long", "required": False},
        {"id": 6, "name": "churn_probability", "type": "double", "required": False},
        {"id": 7, "name": "health_score", "type": "double", "required": False},
        {"id": 8, "name": "scored_at", "type": "timestamp", "required": False},
    ],
    "support_analytics_rollup": [
        {"id": 1, "name": "period", "type": "string", "required": False},
        {"id": 2, "name": "total_tickets", "type": "long", "required": False},
        {"id": 3, "name": "avg_resolution_hours", "type": "double", "required": False},
        {"id": 4, "name": "csat_score", "type": "double", "required": False},
        {"id": 5, "name": "agent_id", "type": "string", "required": False},
        {"id": 6, "name": "sla_met_pct", "type": "double", "required": False},
        {"id": 7, "name": "escalation_rate", "type": "double", "required": False},
        {"id": 8, "name": "computed_at", "type": "timestamp", "required": False},
    ],
    "executive_kpi_snapshot": [
        {"id": 1, "name": "snapshot_date", "type": "date", "required": False},
        {"id": 2, "name": "total_revenue", "type": "double", "required": False},
        {"id": 3, "name": "mrr", "type": "double", "required": False},
        {"id": 4, "name": "active_customers", "type": "long", "required": False},
        {"id": 5, "name": "churn_rate", "type": "double", "required": False},
        {"id": 6, "name": "avg_health_score", "type": "double", "required": False},
        {"id": 7, "name": "nps_score", "type": "double", "required": False},
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
