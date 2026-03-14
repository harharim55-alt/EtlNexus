"""Bouncer service — business logic for bouncer listing and topology traversal."""

import logging
from collections import defaultdict

from app.cache import bouncer_cache, bouncer_topology_cache
from app.repositories.bouncer_repo import BouncerRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.bouncer import (
    BouncerListResponse,
    BouncerResponse,
    BouncerTopologyNode,
    BouncerTopologyResponse,
)

logger = logging.getLogger(__name__)


class BouncerService:
    def __init__(
        self,
        bouncer_repo: BouncerRepository,
        dag_task_repo: DagTaskRepository,
        pipeline_repo: PipelineRepository,
    ):
        self.bouncer_repo = bouncer_repo
        self.dag_task_repo = dag_task_repo
        self.pipeline_repo = pipeline_repo

    async def get_all_bouncers(self, team: str | None = None) -> BouncerListResponse:
        cache_key = f"bouncers:{team or 'all'}"
        cached = bouncer_cache.get(cache_key)
        if cached is not None:
            return cached

        if team:
            bouncers = await self.bouncer_repo.get_by_team(team)
        else:
            bouncers = await self.bouncer_repo.get_all()

        teams = await self.bouncer_repo.get_all_teams()

        items = [
            BouncerResponse(
                id=str(s.id),
                bouncer_name=s.bouncer_name,
                display_name=s.display_name,
                description=s.description,
                team=s.team,
                volume_per_day=s.volume_per_day,
                status=s.status,
                dag_ids=s.dag_ids or [],
            )
            for s in bouncers
        ]

        result = BouncerListResponse(bouncers=items, teams=teams)
        bouncer_cache.set(cache_key, result)
        return result

    async def get_bouncer_topology(
        self, bouncer_names: list[str], mode: str = "union"
    ) -> BouncerTopologyResponse:
        cache_key = f"topo:{'|'.join(sorted(bouncer_names))}:{mode}"
        cached = bouncer_topology_cache.get(cache_key)
        if cached is not None:
            return cached

        # Build full dag_task graph for BFS traversal
        all_dag_tasks = await self.dag_task_repo.get_all_entries()

        # Index: (dag_id, task_id) -> dag_task entry
        task_index: dict[tuple[str, str], object] = {}
        # Index: task_id -> list of dag_task entries
        task_by_id: dict[str, list] = defaultdict(list)
        for dt in all_dag_tasks:
            task_index[(dt.dag_id, dt.task_id)] = dt
            task_by_id[dt.task_id].append(dt)

        # Build pipeline lookup (lightweight — no eager-loaded relationships)
        task_id_to_pipeline = await self.pipeline_repo.get_task_id_map()

        # Status map
        status_map: dict[str, str] = {
            tid: p.status for tid, p in task_id_to_pipeline.items()
            if p.status != "unknown"
        }

        # BFS from each selected bouncer, collecting downstream ETLs
        bouncer_to_reachable: dict[str, set[tuple[str, str]]] = {}

        for bouncer_name in bouncer_names:
            reachable: set[tuple[str, str]] = set()  # (dag_id, task_id)
            # Find all dag_task entries for this bouncer
            bouncer_entries = [
                dt for dt in all_dag_tasks if dt.bouncer_name == bouncer_name
            ]

            for entry in bouncer_entries:
                dag_id = entry.dag_id
                # BFS from this bouncer task in this DAG
                queue = list(entry.downstream_task_ids or [])
                visited: set[str] = set()

                while queue:
                    tid = queue.pop(0)
                    if tid in visited:
                        continue
                    visited.add(tid)

                    # Only include ETL tasks (those with pipeline_id, not bouncers)
                    dt_entry = task_index.get((dag_id, tid))
                    if dt_entry and not dt_entry.bouncer_name:
                        reachable.add((dag_id, tid))
                        # Continue BFS through downstream
                        for downstream_tid in dt_entry.downstream_task_ids or []:
                            if downstream_tid not in visited:
                                queue.append(downstream_tid)

            bouncer_to_reachable[bouncer_name] = reachable

        # Apply mode: union or intersection
        if not bouncer_to_reachable:
            all_reachable: set[tuple[str, str]] = set()
        elif mode == "intersection":
            sets = list(bouncer_to_reachable.values())
            all_reachable = sets[0].copy()
            for s in sets[1:]:
                all_reachable &= s
        else:  # union
            all_reachable = set()
            for s in bouncer_to_reachable.values():
                all_reachable |= s

        # Build reverse map: (dag_id, task_id) -> which bouncers reach it
        etl_bouncers: dict[tuple[str, str], list[str]] = defaultdict(list)
        for bouncer_name, reachable in bouncer_to_reachable.items():
            for key in reachable:
                if key in all_reachable:
                    etl_bouncers[key].append(bouncer_name)

        # Build response nodes
        nodes: list[BouncerTopologyNode] = []
        seen_tasks: set[str] = set()

        for dag_id, task_id in sorted(all_reachable):
            # Deduplicate by task_id (show once, with first dag_id)
            if task_id in seen_tasks:
                continue
            seen_tasks.add(task_id)

            pipeline = task_id_to_pipeline.get(task_id)
            nodes.append(
                BouncerTopologyNode(
                    task_id=task_id,
                    pipeline_name=pipeline.name if pipeline else None,
                    pipeline_id=str(pipeline.id) if pipeline else None,
                    status=status_map.get(task_id, "unknown"),
                    dag_id=dag_id,
                    depends_on_bouncers=sorted(
                        set(etl_bouncers.get((dag_id, task_id), []))
                    ),
                )
            )

        result = BouncerTopologyResponse(
            selected_bouncers=bouncer_names,
            downstream_etls=nodes,
            total_etl_count=len(nodes),
        )
        bouncer_topology_cache.set(cache_key, result)
        return result
