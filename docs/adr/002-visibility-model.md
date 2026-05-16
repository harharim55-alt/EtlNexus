# ADR-002: Team-Based Visibility with Grant Extensions

## Status
Accepted

## Context
Pipelines are owned by teams. Users should see their own team's pipelines by default, with the ability for admins to grant cross-team visibility.

## Decision
- Admins see all pipelines
- Non-admin users see: own team's pipelines + unassigned pipelines + pipelines/teams granted via visibility_grants
- Visibility grants support two types: per-pipeline and per-source-team
- Each grant has a level: "viewer" (read) or "editor" (read + write)
- Sub-resource endpoints (lineage, topology, resources, etc.) enforce the same visibility as the pipeline list

## Consequences
- All pipeline sub-resource endpoints must check visibility via `require_pipeline_visibility()` dependency
- Cache keys for user-facing data must include user context to prevent cross-user cache leakage
- The AI chat catalog context must be filtered by user visibility
