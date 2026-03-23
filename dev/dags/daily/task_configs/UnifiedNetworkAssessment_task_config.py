"""Unified Network Assessment — Comprehensive per-IP network health scoring."""

needs = [
    "NetflowCapture",
    "SwitchPortCollector",
    "BandwidthBillingAggregator",
    "ThreatScoringPipeline",
    "DhcpLeaseSync",
    "EndpointActivityScoring",
]
prefers = ["SyslogEventStream"]
