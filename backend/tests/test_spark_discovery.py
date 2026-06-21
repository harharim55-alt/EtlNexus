"""get_all_schemas namespace discovery + iceberg/exclusion filters — mocked Spark."""

from unittest.mock import MagicMock, patch

from app.config import settings
from app.integrations.spark_connect_client import SparkConnectClient, SparkTableSchema


def _client():
    c = SparkConnectClient()
    c._get_spark = MagicMock(return_value=object())  # pretend reachable
    return c


def _schema(ns, t):
    return SparkTableSchema(table_name=t, namespace=ns, fields=[{"name": "id", "type": "BIGINT"}])


def test_discovers_all_namespaces_when_prefix_empty(monkeypatch):
    monkeypatch.setattr(settings, "spark_excluded_namespaces", "")
    c = _client()
    c.namespace_prefix = ""
    tables = {"prism": ["Orders"], "vault": ["Logs", "Audit"]}
    with patch.object(c, "list_namespaces", return_value=["prism", "vault"]) as ln, \
         patch.object(c, "list_tables_in_namespace", side_effect=lambda ns: tables[ns]), \
         patch.object(c, "is_iceberg_table", return_value=True), \
         patch.object(c, "get_table_schema", side_effect=_schema):
        out = c.get_all_schemas()
    ln.assert_called_once()
    assert {(s.namespace, s.table_name) for s in out} == {("prism", "Orders"), ("vault", "Logs"), ("vault", "Audit")}


def test_explicit_prefix_skips_namespace_discovery(monkeypatch):
    monkeypatch.setattr(settings, "spark_excluded_namespaces", "")
    c = _client()
    c.namespace_prefix = "prism"
    with patch.object(c, "list_namespaces") as ln, \
         patch.object(c, "list_tables_in_namespace", return_value=["Orders"]), \
         patch.object(c, "is_iceberg_table", return_value=True), \
         patch.object(c, "get_table_schema", side_effect=_schema):
        out = c.get_all_schemas()
    ln.assert_not_called()
    assert {(s.namespace, s.table_name) for s in out} == {("prism", "Orders")}


def test_skips_excluded_namespaces_and_non_iceberg(monkeypatch):
    monkeypatch.setattr(settings, "spark_excluded_namespaces", "information_schema")
    c = _client()
    c.namespace_prefix = ""
    tables = {"prism": ["RealTable", "AView"], "information_schema": ["columns"]}
    # AView is not an Iceberg table -> excluded.
    with patch.object(c, "list_namespaces", return_value=["prism", "information_schema"]), \
         patch.object(c, "list_tables_in_namespace", side_effect=lambda ns: tables[ns]), \
         patch.object(c, "is_iceberg_table", side_effect=lambda ns, t: t == "RealTable"), \
         patch.object(c, "get_table_schema", side_effect=_schema):
        out = c.get_all_schemas()
    # information_schema excluded entirely; AView dropped (not iceberg).
    assert {(s.namespace, s.table_name) for s in out} == {("prism", "RealTable")}
