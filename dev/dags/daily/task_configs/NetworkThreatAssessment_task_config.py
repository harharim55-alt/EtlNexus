"""Network Threat Assessment — Comprehensive per-IP network health scoring."""

needs = [
    "FlowInterceptor",
    "PortScanCollector",
    "BandwidthAnalyzer",
    "ThreatHunterScorer",
    "DhcpLeaseRecon",
    "EndpointRiskScorer",
]
prefers = ["SyslogCollector"]
