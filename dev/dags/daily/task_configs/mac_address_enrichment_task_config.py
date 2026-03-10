"""MAC Address Enrichment — Enriches MAC addresses with DHCP and HTTP access data."""

needs = ["dhcp_lease_sync", "http_access_log_ingest"]
prefers = []
