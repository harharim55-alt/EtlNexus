# ADR-001: In-Memory TTL Cache Design

## Status
Accepted

## Context
The application needs caching for frequently-accessed data (pipeline lists, topology, schema matrix) to reduce database load. The deployment model is a single backend process.

## Decision
Use process-local in-memory TTL caches (Python dict-based) with sync-cycle invalidation.

## Decision Update
A Redis pub/sub cache-invalidation bus was briefly added for cross-instance
invalidation, then **removed**: the project mandates no external services (only
frontend, backend, and Postgres). Caching is in-memory and process-local only.

## Consequences
- Simple, zero-dependency, fast for single-process deployment
- Cache invalidation via `clear_all()` only affects the local process
- Each backend instance in a multi-instance deployment keeps its own cache state; instances converge via TTL expiry (no cross-instance invalidation)
- APScheduler runs per-process — multiple instances will run duplicate sync jobs

## Migration Path
If cross-instance cache coherence becomes necessary, the options are an external
shared cache or a pub/sub invalidation bus — both deliberately out of scope under
the current "no external services" requirement. Prefer lowering TTLs or a single
backend instance instead.
