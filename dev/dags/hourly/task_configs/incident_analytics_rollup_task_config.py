"""Incident Analytics Rollup — Aggregates incident metrics with DNS context."""

needs = ["syslog_event_stream"]
prefers = ["dns_record_sync"]
