"""Device Fingerprint Enrichment — Unified device profile from port, route, and DNS data."""

needs = ["switch_port_collector", "bgp_route_sync"]
prefers = ["dns_record_sync"]
