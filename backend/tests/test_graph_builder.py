"""Tests for app.services.graph_builder — pure BFS graph algorithms.

All functions are stateless and operate on plain Python data structures
(dicts, sets, deques).  No DB or ORM dependencies.
"""

from unittest.mock import MagicMock

from app.services.graph_builder import (
    bfs_bouncer_discovery,
    bfs_find_bouncers,
    bfs_upstream_semantic,
    connect_bouncers_forward,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_dag_task(
    *,
    task_id: str,
    bouncer_name: str | None = None,
    needs: list[str] | None = None,
    prefers: list[str] | None = None,
    downstream_task_ids: list[str] | None = None,
):
    """Lightweight DagTask-like mock for graph algorithm tests."""
    dt = MagicMock()
    dt.task_id = task_id
    dt.bouncer_name = bouncer_name
    dt.needs = needs
    dt.prefers = prefers
    dt.downstream_task_ids = downstream_task_ids or []
    return dt


# ---------------------------------------------------------------------------
# bfs_find_bouncers
# ---------------------------------------------------------------------------


class TestBfsFindBouncers:
    def test_linear_chain_finds_bouncer(self):
        """A -> B -> C(bouncer): traversing upstream from A finds C."""
        dag_id = "dag1"
        dt_a = make_dag_task(task_id="A")
        dt_b = make_dag_task(task_id="B")
        dt_c = make_dag_task(task_id="C", bouncer_name="BouncerC")

        dag_tasks_by_dag = {dag_id: [dt_a, dt_b, dt_c]}
        # reverse_adj: maps task to its upstream predecessors
        # C -> B -> A (downstream direction), so reverse: A's upstream is B, B's upstream is C
        reverse_adj = {
            dag_id: {
                "A": {"B"},
                "B": {"C"},
            }
        }

        result = bfs_find_bouncers("A", dag_tasks_by_dag, reverse_adj, {dag_id})

        assert "BouncerC" in result
        assert dag_id in result["BouncerC"]

    def test_diamond_graph_no_duplicates(self):
        """A -> B, A -> C, B -> D(bouncer), C -> D(bouncer): finds D once."""
        dag_id = "dag1"
        dt_a = make_dag_task(task_id="A")
        dt_b = make_dag_task(task_id="B")
        dt_c = make_dag_task(task_id="C")
        dt_d = make_dag_task(task_id="D", bouncer_name="BouncerD")

        dag_tasks_by_dag = {dag_id: [dt_a, dt_b, dt_c, dt_d]}
        reverse_adj = {
            dag_id: {
                "A": {"B", "C"},
                "B": {"D"},
                "C": {"D"},
            }
        }

        result = bfs_find_bouncers("A", dag_tasks_by_dag, reverse_adj, {dag_id})

        assert "BouncerD" in result
        assert len(result) == 1  # only one bouncer found
        assert dag_id in result["BouncerD"]

    def test_no_bouncers_returns_empty(self):
        """Graph with no bouncer tasks returns an empty dict."""
        dag_id = "dag1"
        dt_a = make_dag_task(task_id="A")
        dt_b = make_dag_task(task_id="B")

        dag_tasks_by_dag = {dag_id: [dt_a, dt_b]}
        reverse_adj = {dag_id: {"A": {"B"}}}

        result = bfs_find_bouncers("A", dag_tasks_by_dag, reverse_adj, {dag_id})

        assert result == {}

    def test_empty_graph_returns_empty(self):
        """No adjacency data at all returns empty."""
        result = bfs_find_bouncers("A", {}, {}, set())
        assert result == {}

    def test_multiple_dags_finds_bouncers_in_each(self):
        """Bouncers discovered independently per active DAG."""
        dt_a1 = make_dag_task(task_id="A")
        dt_b1 = make_dag_task(task_id="Bouncer1", bouncer_name="Bouncer1")
        dt_a2 = make_dag_task(task_id="A")
        dt_b2 = make_dag_task(task_id="Bouncer2", bouncer_name="Bouncer2")

        dag_tasks_by_dag = {
            "dag1": [dt_a1, dt_b1],
            "dag2": [dt_a2, dt_b2],
        }
        reverse_adj = {
            "dag1": {"A": {"Bouncer1"}},
            "dag2": {"A": {"Bouncer2"}},
        }

        result = bfs_find_bouncers("A", dag_tasks_by_dag, reverse_adj, {"dag1", "dag2"})

        assert "Bouncer1" in result
        assert "Bouncer2" in result
        assert "dag1" in result["Bouncer1"]
        assert "dag2" in result["Bouncer2"]

    def test_bouncer_is_terminal(self):
        """BFS does not continue past bouncer tasks (they are terminal roots)."""
        dag_id = "dag1"
        dt_a = make_dag_task(task_id="A")
        dt_bouncer = make_dag_task(task_id="B", bouncer_name="BouncerB")
        dt_c = make_dag_task(task_id="C", bouncer_name="BouncerC")

        dag_tasks_by_dag = {dag_id: [dt_a, dt_bouncer, dt_c]}
        # A -> B(bouncer) -> C(bouncer): since B is terminal, C should NOT be found
        reverse_adj = {
            dag_id: {
                "A": {"B"},
                "B": {"C"},
            }
        }

        result = bfs_find_bouncers("A", dag_tasks_by_dag, reverse_adj, {dag_id})

        assert "BouncerB" in result
        assert "BouncerC" not in result


# ---------------------------------------------------------------------------
# bfs_upstream_semantic
# ---------------------------------------------------------------------------


class TestBfsUpstreamSemantic:
    def test_simple_needs_chain(self):
        """A needs B, B needs C: returns correct depths."""
        dt_a = make_dag_task(task_id="A", needs=["B"])
        dt_b = make_dag_task(task_id="B", needs=["C"])
        dt_c = make_dag_task(task_id="C")

        tid_to_dt = {"A": dt_a, "B": dt_b, "C": dt_c}

        visited, edges = bfs_upstream_semantic("A", tid_to_dt)

        assert visited["A"] == 0
        assert visited["B"] == 1
        assert visited["C"] == 2
        assert len(visited) == 3

        # Edges: B->A (needs), C->B (needs)
        needs_edges = [(s, t, e) for s, t, e in edges if e == "needs"]
        assert ("B", "A", "needs") in needs_edges
        assert ("C", "B", "needs") in needs_edges

    def test_prefers_edges_recorded(self):
        """Prefers edges are traversed and recorded with 'prefers' type."""
        dt_a = make_dag_task(task_id="A", prefers=["B"])
        dt_b = make_dag_task(task_id="B")

        tid_to_dt = {"A": dt_a, "B": dt_b}

        visited, edges = bfs_upstream_semantic("A", tid_to_dt)

        assert visited["A"] == 0
        assert visited["B"] == 1
        assert ("B", "A", "prefers") in edges

    def test_cycle_handling(self):
        """A needs B, B needs A: visited set prevents infinite loop."""
        dt_a = make_dag_task(task_id="A", needs=["B"])
        dt_b = make_dag_task(task_id="B", needs=["A"])

        tid_to_dt = {"A": dt_a, "B": dt_b}

        visited, edges = bfs_upstream_semantic("A", tid_to_dt)

        assert len(visited) == 2
        assert "A" in visited
        assert "B" in visited

    def test_missing_task_in_map(self):
        """Reference to a task not in tid_to_dt is still visited but not expanded."""
        dt_a = make_dag_task(task_id="A", needs=["B"])

        tid_to_dt = {"A": dt_a}  # B is missing

        visited, edges = bfs_upstream_semantic("A", tid_to_dt)

        assert visited["A"] == 0
        assert visited["B"] == 1  # visited but not expanded
        assert ("B", "A", "needs") in edges

    def test_empty_root(self):
        """Root task with no needs or prefers produces a single node."""
        dt_a = make_dag_task(task_id="A")

        tid_to_dt = {"A": dt_a}

        visited, edges = bfs_upstream_semantic("A", tid_to_dt)

        assert visited == {"A": 0}
        assert edges == []

    def test_mixed_needs_and_prefers(self):
        """Both needs and prefers are traversed from a single task."""
        dt_a = make_dag_task(task_id="A", needs=["B"], prefers=["C"])
        dt_b = make_dag_task(task_id="B")
        dt_c = make_dag_task(task_id="C")

        tid_to_dt = {"A": dt_a, "B": dt_b, "C": dt_c}

        visited, edges = bfs_upstream_semantic("A", tid_to_dt)

        assert len(visited) == 3
        assert ("B", "A", "needs") in edges
        assert ("C", "A", "prefers") in edges


# ---------------------------------------------------------------------------
# bfs_bouncer_discovery
# ---------------------------------------------------------------------------


class TestBfsBouncerDiscovery:
    def test_finds_upstream_bouncer(self):
        """Discovers bouncer reachable via structural reverse edges from visited tasks."""
        dt_a = make_dag_task(task_id="A")
        dt_mid = make_dag_task(task_id="Mid")
        dt_bouncer = make_dag_task(task_id="Bouncer1", bouncer_name="Bouncer1")

        tid_to_dt = {"A": dt_a, "Mid": dt_mid, "Bouncer1": dt_bouncer}
        # visited = semantic BFS result
        visited = {"A": 0}
        # reverse_adj: A's structural upstream is Mid, Mid's upstream is Bouncer1
        reverse_adj = {
            "A": {"Mid"},
            "Mid": {"Bouncer1"},
        }

        result = bfs_bouncer_discovery(visited, tid_to_dt, reverse_adj, "dag1")

        assert "Bouncer1" in result
        assert "dag1" in result["Bouncer1"]

    def test_no_bouncers_returns_empty(self):
        """When no bouncer tasks exist upstream, returns empty."""
        dt_a = make_dag_task(task_id="A")
        dt_b = make_dag_task(task_id="B")

        tid_to_dt = {"A": dt_a, "B": dt_b}
        visited = {"A": 0}
        reverse_adj = {"A": {"B"}}

        result = bfs_bouncer_discovery(visited, tid_to_dt, reverse_adj, "dag1")

        assert result == {}

    def test_skips_already_visited_tasks(self):
        """Tasks already in visited are not re-queued for bouncer discovery."""
        dt_a = make_dag_task(task_id="A")
        dt_b = make_dag_task(task_id="B")

        tid_to_dt = {"A": dt_a, "B": dt_b}
        # Both A and B are already in visited
        visited = {"A": 0, "B": 1}
        reverse_adj = {"A": {"B"}}

        result = bfs_bouncer_discovery(visited, tid_to_dt, reverse_adj, "dag1")

        assert result == {}

    def test_multiple_bouncers_discovered(self):
        """Two bouncer tasks upstream are both found."""
        dt_a = make_dag_task(task_id="A")
        dt_b1 = make_dag_task(task_id="B1", bouncer_name="BouncerAlpha")
        dt_b2 = make_dag_task(task_id="B2", bouncer_name="BouncerBeta")

        tid_to_dt = {"A": dt_a, "B1": dt_b1, "B2": dt_b2}
        visited = {"A": 0}
        reverse_adj = {"A": {"B1", "B2"}}

        result = bfs_bouncer_discovery(visited, tid_to_dt, reverse_adj, "dag1")

        assert "BouncerAlpha" in result
        assert "BouncerBeta" in result

    def test_empty_visited_set(self):
        """Empty visited set means no starting frontier; returns empty."""
        result = bfs_bouncer_discovery({}, {}, {}, "dag1")
        assert result == {}


# ---------------------------------------------------------------------------
# connect_bouncers_forward
# ---------------------------------------------------------------------------


class TestConnectBouncersForward:
    def test_forward_walk_finds_visited_etl(self):
        """Bouncer -> EtlA (visited): connection recorded."""
        dt_bouncer = make_dag_task(
            task_id="BouncerX", bouncer_name="BouncerX",
            downstream_task_ids=["EtlA"],
        )
        dt_etl_a = make_dag_task(task_id="EtlA")

        tid_to_dt = {"BouncerX": dt_bouncer, "EtlA": dt_etl_a}
        visited = {"EtlA": 0}
        found_bouncers = {"BouncerX": {"dag1"}}

        result = connect_bouncers_forward(found_bouncers, tid_to_dt, visited)

        assert ("BouncerX", "EtlA") in result

    def test_multi_hop_forward_walk(self):
        """Bouncer -> Mid -> EtlA (visited): connection recorded through intermediate."""
        dt_bouncer = make_dag_task(
            task_id="BouncerY", bouncer_name="BouncerY",
            downstream_task_ids=["Mid"],
        )
        dt_mid = make_dag_task(task_id="Mid", downstream_task_ids=["EtlA"])
        dt_etl_a = make_dag_task(task_id="EtlA")

        tid_to_dt = {"BouncerY": dt_bouncer, "Mid": dt_mid, "EtlA": dt_etl_a}
        visited = {"EtlA": 0}
        found_bouncers = {"BouncerY": {"dag1"}}

        result = connect_bouncers_forward(found_bouncers, tid_to_dt, visited)

        assert ("BouncerY", "EtlA") in result

    def test_no_connection_to_visited(self):
        """Bouncer's downstream does not reach any visited task: no connections."""
        dt_bouncer = make_dag_task(
            task_id="BouncerZ", bouncer_name="BouncerZ",
            downstream_task_ids=["Unrelated"],
        )
        dt_unrelated = make_dag_task(task_id="Unrelated")

        tid_to_dt = {"BouncerZ": dt_bouncer, "Unrelated": dt_unrelated}
        visited = {"EtlA": 0}
        found_bouncers = {"BouncerZ": {"dag1"}}

        result = connect_bouncers_forward(found_bouncers, tid_to_dt, visited)

        assert result == []

    def test_stops_at_visited_task(self):
        """Forward walk stops at the first visited task, not continuing past it."""
        dt_bouncer = make_dag_task(
            task_id="BouncerW", bouncer_name="BouncerW",
            downstream_task_ids=["EtlA"],
        )
        dt_etl_a = make_dag_task(task_id="EtlA", downstream_task_ids=["EtlB"])
        dt_etl_b = make_dag_task(task_id="EtlB")

        tid_to_dt = {"BouncerW": dt_bouncer, "EtlA": dt_etl_a, "EtlB": dt_etl_b}
        visited = {"EtlA": 0, "EtlB": 1}
        found_bouncers = {"BouncerW": {"dag1"}}

        result = connect_bouncers_forward(found_bouncers, tid_to_dt, visited)

        # Should connect to EtlA but NOT traverse to EtlB
        assert ("BouncerW", "EtlA") in result
        assert ("BouncerW", "EtlB") not in result

    def test_multiple_bouncers_multiple_connections(self):
        """Multiple bouncers each connect to different visited tasks."""
        dt_b1 = make_dag_task(
            task_id="B1", bouncer_name="B1",
            downstream_task_ids=["EtlA"],
        )
        dt_b2 = make_dag_task(
            task_id="B2", bouncer_name="B2",
            downstream_task_ids=["EtlB"],
        )
        dt_etl_a = make_dag_task(task_id="EtlA")
        dt_etl_b = make_dag_task(task_id="EtlB")

        tid_to_dt = {"B1": dt_b1, "B2": dt_b2, "EtlA": dt_etl_a, "EtlB": dt_etl_b}
        visited = {"EtlA": 0, "EtlB": 1}
        found_bouncers = {"B1": {"dag1"}, "B2": {"dag1"}}

        result = connect_bouncers_forward(found_bouncers, tid_to_dt, visited)

        assert ("B1", "EtlA") in result
        assert ("B2", "EtlB") in result

    def test_empty_found_bouncers(self):
        """No bouncers to connect returns empty list."""
        result = connect_bouncers_forward({}, {}, {"EtlA": 0})
        assert result == []

    def test_bouncer_not_in_tid_map(self):
        """Bouncer name not in tid_to_dt is safely skipped."""
        found_bouncers = {"MissingBouncer": {"dag1"}}
        result = connect_bouncers_forward(found_bouncers, {}, {"EtlA": 0})
        assert result == []
