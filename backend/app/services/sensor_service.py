"""Sensor service — business logic for sensor listing and topology traversal."""

import logging
from collections import defaultdict

from app.cache import sensor_cache, sensor_topology_cache
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.sensor_repo import SensorRepository
from app.schemas.sensor import (
    SensorListResponse,
    SensorResponse,
    SensorTopologyNode,
    SensorTopologyResponse,
)

logger = logging.getLogger(__name__)


class SensorService:
    def __init__(
        self,
        sensor_repo: SensorRepository,
        dag_task_repo: DagTaskRepository,
        pipeline_repo: PipelineRepository,
    ):
        self.sensor_repo = sensor_repo
        self.dag_task_repo = dag_task_repo
        self.pipeline_repo = pipeline_repo

    async def get_all_sensors(self, team: str | None = None) -> SensorListResponse:
        cache_key = f"sensors:{team or 'all'}"
        cached = sensor_cache.get(cache_key)
        if cached is not None:
            return cached

        if team:
            sensors = await self.sensor_repo.get_by_team(team)
        else:
            sensors = await self.sensor_repo.get_all()

        teams = await self.sensor_repo.get_all_teams()

        items = [
            SensorResponse(
                id=str(s.id),
                sensor_name=s.sensor_name,
                display_name=s.display_name,
                description=s.description,
                team=s.team,
                volume_per_day=s.volume_per_day,
                status=s.status,
                dag_ids=s.dag_ids or [],
            )
            for s in sensors
        ]

        result = SensorListResponse(sensors=items, teams=teams)
        sensor_cache.set(cache_key, result)
        return result

    async def get_sensor_topology(
        self, sensor_names: list[str], mode: str = "union"
    ) -> SensorTopologyResponse:
        cache_key = f"topo:{'|'.join(sorted(sensor_names))}:{mode}"
        cached = sensor_topology_cache.get(cache_key)
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

        # Build pipeline lookup
        all_pipelines = await self.pipeline_repo.get_all()
        task_id_to_pipeline: dict[str, object] = {}
        for p in all_pipelines:
            tid = p.task_id or p.name.lower().replace(" ", "_")
            task_id_to_pipeline[tid] = p

        # Status map
        status_map: dict[str, str] = {}
        for p in all_pipelines:
            tid = p.task_id or p.name.lower().replace(" ", "_")
            if p.airflow_status:
                status_map[tid] = p.airflow_status.status

        # BFS from each selected sensor, collecting downstream ETLs
        # Track which sensors reach which ETL task
        sensor_to_reachable: dict[str, set[tuple[str, str]]] = {}

        for sensor_name in sensor_names:
            reachable: set[tuple[str, str]] = set()  # (dag_id, task_id)
            # Find all dag_task entries for this sensor
            sensor_entries = [
                dt for dt in all_dag_tasks if dt.sensor_name == sensor_name
            ]

            for entry in sensor_entries:
                dag_id = entry.dag_id
                # BFS from this sensor task in this DAG
                queue = list(entry.downstream_task_ids or [])
                visited: set[str] = set()

                while queue:
                    tid = queue.pop(0)
                    if tid in visited:
                        continue
                    visited.add(tid)

                    # Only include ETL tasks (those with pipeline_id, not sensors)
                    dt_entry = task_index.get((dag_id, tid))
                    if dt_entry and not dt_entry.sensor_name:
                        reachable.add((dag_id, tid))
                        # Continue BFS through downstream
                        for downstream_tid in dt_entry.downstream_task_ids or []:
                            if downstream_tid not in visited:
                                queue.append(downstream_tid)

            sensor_to_reachable[sensor_name] = reachable

        # Apply mode: union or intersection
        if not sensor_to_reachable:
            all_reachable: set[tuple[str, str]] = set()
        elif mode == "intersection":
            sets = list(sensor_to_reachable.values())
            all_reachable = sets[0].copy()
            for s in sets[1:]:
                all_reachable &= s
        else:  # union
            all_reachable = set()
            for s in sensor_to_reachable.values():
                all_reachable |= s

        # Build reverse map: (dag_id, task_id) -> which sensors reach it
        etl_sensors: dict[tuple[str, str], list[str]] = defaultdict(list)
        for sensor_name, reachable in sensor_to_reachable.items():
            for key in reachable:
                if key in all_reachable:
                    etl_sensors[key].append(sensor_name)

        # Build response nodes
        nodes: list[SensorTopologyNode] = []
        seen_tasks: set[str] = set()

        for dag_id, task_id in sorted(all_reachable):
            # Deduplicate by task_id (show once, with first dag_id)
            if task_id in seen_tasks:
                continue
            seen_tasks.add(task_id)

            pipeline = task_id_to_pipeline.get(task_id)
            nodes.append(
                SensorTopologyNode(
                    task_id=task_id,
                    pipeline_name=pipeline.name if pipeline else None,
                    pipeline_id=str(pipeline.id) if pipeline else None,
                    status=status_map.get(task_id, "unknown"),
                    dag_id=dag_id,
                    depends_on_sensors=sorted(
                        set(etl_sensors.get((dag_id, task_id), []))
                    ),
                )
            )

        result = SensorTopologyResponse(
            selected_sensors=sensor_names,
            downstream_etls=nodes,
            total_etl_count=len(nodes),
        )
        sensor_topology_cache.set(cache_key, result)
        return result
