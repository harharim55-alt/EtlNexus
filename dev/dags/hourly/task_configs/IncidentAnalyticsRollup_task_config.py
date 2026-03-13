"""Incident Analytics Rollup — Aggregates incident metrics with DNS context."""

needs = ["SyslogEventStream"]
prefers = ["DnsRecordSync"]
