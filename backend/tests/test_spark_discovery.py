"""get_all_schemas namespace discovery — mocked Spark, no real server."""

from unittest.mock import MagicMock, patch

from app.integrations.spark_connect_client import SparkConnectClient, SparkTableSchema


def _client():
    c = SparkConnectClient()
    # Pretend Spark is reachable (truthy session) without touching pyspark.
    c._get_spark = MagicMock(return_value=object())
    return c


def _schema(ns, t):
    return SparkTableSchema(table_name=t, namespace=ns, fields=[{"name": "id", "type": "BIGINT"}])


def test_discovers_all_namespaces_when_prefix_empty():
    c = _client()
    c.namespace_prefix = ""  # empty → discover all
    tables = {"prism": ["Orders"], "vault": ["Logs", "Audit"]}
    with patch.object(c, "list_namespaces", return_value=["prism", "vault"]) as ln, \
         patch.object(c, "list_tables_in_namespace", side_effect=lambda ns: tables[ns]), \
         patch.object(c, "get_table_schema", side_effect=_schema):
        out = c.get_all_schemas()
    ln.assert_called_once()
    got = {(s.namespace, s.table_name) for s in out}
    assert got == {("prism", "Orders"), ("vault", "Logs"), ("vault", "Audit")}


def test_explicit_prefix_skips_namespace_discovery():
    c = _client()
    c.namespace_prefix = "prism"  # explicit → no SHOW NAMESPACES
    with patch.object(c, "list_namespaces") as ln, \
         patch.object(c, "list_tables_in_namespace", return_value=["Orders"]), \
         patch.object(c, "get_table_schema", side_effect=_schema):
        out = c.get_all_schemas()
    ln.assert_not_called()
    assert {(s.namespace, s.table_name) for s in out} == {("prism", "Orders")}
