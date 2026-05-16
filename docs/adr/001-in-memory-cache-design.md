# ADR-001: In-Memory TTL Cache Design

## Status
Accepted

## Context
The application needs caching for frequently-accessed data (pipeline lists, topology, schema matrix) to reduce database load. The deployment model is a single backend process.

## Decision
Use process-local in-memory TTL caches (Python dict-based) with sync-cycle invalidation.

## Consequences
- Simple, zero-dependency, fast for single-process deployment
- Cache invalidation via `clear_all()` only affects the local process
- Horizontal scaling requires migration to Redis or shared cache
- Each backend instance in a multi-instance deployment will have its own cache state
- APScheduler runs per-process — multiple instances will run duplicate sync jobs

## Migration Path
When horizontal scaling is needed: replace TTLCache with Redis-backed cache, externalize APScheduler to use Redis as job store, designate a single scheduler instance.
