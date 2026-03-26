"""Pure graph algorithms for pipeline topology construction.

All functions in this module are stateless and operate exclusively on plain
Python data structures (dicts, lists, sets).  There are no database queries,
no SQLAlchemy imports, and no schema-object construction — those concerns
remain in topology_service.py.
"""

from collections import defaultdict


def bfs_find_bouncers(
    root_task_id: str,
    dag_tasks_by_dag: dict[str, list],
    reverse_adj: dict[str, dict[str, set[str]]],
    active_dag_ids: set[str],
) -> dict[str, set[str]]:
    """BFS through the reverse adjacency graph to find upstream bouncer tasks.

    For every active DAG, performs a reverse BFS starting from *root_task_id*
    and walks upstream through ``reverse_adj``.  When a task that carries a
    ``bouncer_name`` is encountered it is recorded as a terminal root (the
    traversal does not continue beyond it).

    Args:
        root_task_id: The task_id of the pipeline whose ancestors we are
            exploring.
        dag_tasks_by_dag: Mapping ``dag_id -> list[DagTask]``.  Each DagTask
            object must expose ``task_id`` and ``bouncer_name`` attributes.
        reverse_adj: Nested mapping ``dag_id -> {task_id -> set of upstream
            task_ids}``.  For a given DAG, ``reverse_adj[dag_id][tid]`` gives
            the set of tasks whose *downstream* edges point to ``tid`` (i.e.
            the direct upstream predecessors of ``tid``).
        active_dag_ids: The set of DAG ids to traverse.

    Returns:
        A dict mapping ``bouncer_name -> set of dag_ids`` where each bouncer
        was discovered.
    """
    found_bouncers: dict[str, set[str]] = {}

    for adid in active_dag_ids:
        tid_to_dt = {dt.task_id: dt for dt in dag_tasks_by_dag.get(adid, [])}
        visited: set[str] = set()
        queue: list[str] = [root_task_id]

        while queue:
            tid = queue.pop(0)
            if tid in visited:
                continue
            visited.add(tid)

            dt_entry = tid_to_dt.get(tid)
            if dt_entry and dt_entry.bouncer_name:
                found_bouncers.setdefault(dt_entry.bouncer_name, set()).add(adid)
                continue  # bouncers are terminal roots — do not traverse further

            for upstream_tid in reverse_adj.get(adid, {}).get(tid, set()):
                if upstream_tid not in visited:
                    queue.append(upstream_tid)

    return found_bouncers


def bfs_upstream_semantic(
    root_task_id: str,
    tid_to_dt: dict,
) -> tuple[dict[str, int], list[tuple[str, str, str]]]:
    """BFS on semantic (needs/prefers) dependency edges from a root task.

    Starting from *root_task_id*, follows ``.needs`` and ``.prefers`` lists on
    each DagTask object to recursively discover the full upstream dependency
    subgraph.

    Args:
        root_task_id: The starting task_id for the BFS.
        tid_to_dt: Mapping ``task_id -> DagTask``.  Each DagTask must expose
            ``.needs`` and ``.prefers`` attributes (both ``list[str] | None``).

    Returns:
        A 2-tuple ``(visited, edges)`` where:

        - ``visited`` is a dict mapping each reached ``task_id`` to its BFS
          depth (0 for the root).
        - ``edges`` is a list of ``(source_task_id, target_task_id,
          edge_type)`` tuples where ``edge_type`` is ``"needs"`` or
          ``"prefers"``.  ``source_task_id`` is the upstream dependency and
          ``target_task_id`` is the depending task (the direction follows
          data-flow: source produces data consumed by target).
    """
    visited: dict[str, int] = {}
    edges: list[tuple[str, str, str]] = []
    queue: list[tuple[str, int]] = [(root_task_id, 0)]

    while queue:
        tid, depth = queue.pop(0)
        if tid in visited:
            continue
        visited[tid] = depth

        dt = tid_to_dt.get(tid)
        if not dt:
            continue

        for dep_tid in dt.needs or []:
            edges.append((dep_tid, tid, "needs"))
            if dep_tid not in visited:
                queue.append((dep_tid, depth + 1))

        for dep_tid in dt.prefers or []:
            edges.append((dep_tid, tid, "prefers"))
            if dep_tid not in visited:
                queue.append((dep_tid, depth + 1))

    return visited, edges


def bfs_bouncer_discovery(
    visited: dict[str, int],
    tid_to_dt: dict,
    reverse_adj: dict[str, set[str]],
    active_dag_id: str,
) -> dict[str, set[str]]:
    """Reverse-graph BFS from visited tasks to discover upstream bouncer tasks.

    Starting from all tasks already in *visited* (the semantic BFS result),
    walks the structural reverse adjacency graph to find any upstream bouncer
    tasks that feed into the visited subgraph but were not reachable via
    needs/prefers edges.

    Args:
        visited: Mapping of ``task_id -> depth`` produced by
            ``bfs_upstream_semantic``.  Used both as the starting frontier and
            as a guard — tasks already in *visited* are skipped.
        tid_to_dt: Mapping ``task_id -> DagTask``.  Each DagTask must expose a
            ``bouncer_name`` attribute.
        reverse_adj: Flat mapping ``task_id -> set of upstream task_ids`` for
            the single active DAG.
        active_dag_id: The DAG id string to record in the returned dict for
            each discovered bouncer.

    Returns:
        A dict mapping ``bouncer_name -> set of dag_ids`` where each bouncer
        was discovered.
    """
    found_bouncers: dict[str, set[str]] = {}
    bouncer_visited: set[str] = set()
    bouncer_queue: list[str] = list(visited.keys())

    while bouncer_queue:
        tid = bouncer_queue.pop(0)
        if tid in bouncer_visited:
            continue
        bouncer_visited.add(tid)

        for upstream_tid in reverse_adj.get(tid, set()):
            if upstream_tid in bouncer_visited:
                continue
            dt_entry = tid_to_dt.get(upstream_tid)
            if dt_entry and dt_entry.bouncer_name:
                found_bouncers.setdefault(dt_entry.bouncer_name, set()).add(active_dag_id)
            elif upstream_tid not in visited:
                bouncer_queue.append(upstream_tid)

    return found_bouncers


def connect_bouncers_forward(
    found_bouncers: dict[str, set[str]],
    tid_to_dt: dict,
    visited: dict[str, int],
) -> list[tuple[str, str]]:
    """Forward traversal from bouncer tasks to find their connections to visited ETL tasks.

    For each bouncer in *found_bouncers*, performs a forward BFS starting from
    the bouncer task's own downstream edges.  When a visited ETL task is
    encountered, the connection is recorded and that branch is not traversed
    further (preventing redundant transitive connections).

    Args:
        found_bouncers: Mapping of ``bouncer_name -> set of dag_ids`` as
            returned by ``bfs_bouncer_discovery``.  Keys are the task_ids of
            the bouncer tasks themselves.
        tid_to_dt: Mapping ``task_id -> DagTask``.  Each DagTask must expose a
            ``downstream_task_ids`` attribute (``list[str] | None``).
        visited: Mapping of ``task_id -> depth`` for the semantic-BFS visited
            set.  Used to identify which tasks are ETL pipeline nodes.

    Returns:
        A list of ``(bouncer_name, connected_task_id)`` tuples representing
        directed edges from a bouncer to a visited ETL task it feeds into.
    """
    connections: list[tuple[str, str]] = []

    for sname in sorted(found_bouncers.keys()):
        bouncer_dt = tid_to_dt.get(sname)
        if not bouncer_dt:
            continue

        fwd_queue: list[str] = list(bouncer_dt.downstream_task_ids or [])
        fwd_seen: set[str] = set()

        while fwd_queue:
            next_tid = fwd_queue.pop(0)
            if next_tid in fwd_seen:
                continue
            fwd_seen.add(next_tid)

            if next_tid in visited:
                connections.append((sname, next_tid))
                continue  # do not traverse further past a matched ETL task

            dt_next = tid_to_dt.get(next_tid)
            if dt_next:
                for dtid in dt_next.downstream_task_ids or []:
                    if dtid not in fwd_seen:
                        fwd_queue.append(dtid)

    return connections
