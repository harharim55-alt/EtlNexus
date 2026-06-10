# etlnexus-hooks

Auto-instrumentation for EtlNexus — emit structured log markers from BaseETL subclasses with zero per-ETL changes.

## Installation

```bash
pip install etlnexus-hooks
```

## Quick Start

Add the mixin to your `BaseETL` class — **one change instruments all ETLs**:

```python
from etlnexus_hooks import EtlNexusMixin

class BaseETL(EtlNexusMixin):
    def __init__(self, start_date, end_date=None, schedule="daily"):
        ...  # unchanged

    def extract(self):
        raise NotImplementedError

    def transform(self):
        raise NotImplementedError

    def load(self):
        raise NotImplementedError

    def run(self):  # This is now handled by the mixin
        self.extract()
        self.transform()
        self.load()
```

The mixin overrides `run()` to automatically:

| Marker | Source | What it captures |
|--------|--------|------------------|
| `ETL_DESCRIPTION:` | ETL file path | `dagger/PortScanCollector.py` |
| `ETL_WRITES_TO:` | Spark write interception + `SUFFIXES` | All Iceberg tables written |
| `ETL_RESOURCE_ACTUAL:` | Spark StatusStore metrics | Shuffle bytes, I/O, row counts |
| `ETL_EXECUTION_PLAN:` | Spark plan graph | Full execution plan tree |

## Alternative: Decorator

If you can't modify BaseETL's inheritance, use the decorator on individual classes:

```python
from etlnexus_hooks import etlnexus_instrument

@etlnexus_instrument
class MyETL(BaseETL):
    ...
```

## What you still need in DAG definitions

The hooks package automates output markers, but **lineage input declarations** still require `params` in your Airflow DAG tasks:

```python
PythonOperator(
    task_id="MyETL",
    python_callable=run_etl,
    params={
        "needs": ["UpstreamETL"],    # Hard dependencies → reads_from edges
        "prefers": ["OptionalETL"],  # Soft dependencies
    },
    op_kwargs={
        "etl_name": "MyETL",
        "resources": {...},  # Optional
    },
)
```

The mixin cannot distinguish `needs` from `prefers` by intercepting Spark reads — this semantic distinction must come from the DAG definition.
