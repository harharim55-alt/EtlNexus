"""Capacity Metrics API — Serves network capacity metrics to internal dashboards."""

needs = ["PacketInspectionEnrichment"]
prefers = ["ProtocolAdoptionTracker", "EndpointActivityScoring"]
