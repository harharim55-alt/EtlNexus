"""Device Fingerprint Enrichment — Unified device profile from port, route, and DNS data."""

needs = ["SwitchPortCollector", "BgpRouteSync"]
prefers = ["DnsRecordSync"]
