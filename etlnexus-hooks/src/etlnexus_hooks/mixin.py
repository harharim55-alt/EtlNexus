"""EtlNexusMixin — auto-instrumentation for BaseETL subclasses.

Wraps ``run()`` to emit structured log markers that EtlNexus parses from
Airflow task logs.  All introspection is best-effort — failures are logged
but never break the ETL.

Emitted markers:
  ETL_DESCRIPTION:      Relative file path of the ETL class
  ETL_WRITES_TO:        Iceberg table names written during load()
  ETL_RESOURCE_ACTUAL:  Spark resource usage metrics (JSON)
  ETL_EXECUTION_PLAN:   Spark execution plan tree (JSON)
"""

import inspect
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class EtlNexusMixin:
    """Mixin that instruments BaseETL.run() with EtlNexus log markers.

    Add to your BaseETL class::

        from etlnexus_hooks import EtlNexusMixin

        class BaseETL(EtlNexusMixin):
            ...  # everything else unchanged

    The mixin overrides ``run()`` to:

    1. Emit ``ETL_DESCRIPTION:`` (relative file path of the ETL class)
    2. Emit ``ETL_WRITES_TO:`` from module-level ``SUFFIXES`` + intercepted writes
    3. Call the original ``extract() → transform() → load()``
    4. Emit ``ETL_RESOURCE_ACTUAL:`` from Spark metrics
    5. Emit ``ETL_EXECUTION_PLAN:`` from Spark's status store
    """

    def run(self):
        """Instrumented run: emit markers before/after extract → transform → load."""
        etl_name = self.__class__.__name__

        # ── Pre-run: emit description ──
        description = _get_etl_description(self.__class__)
        if description:
            print(f"ETL_DESCRIPTION: {description}")

        # ── Pre-run: emit known SUFFIXES writes ──
        suffixes = _get_module_suffixes(self.__class__)
        print(f"ETL_WRITES_TO: {etl_name}")
        for suffix in suffixes:
            print(f"ETL_WRITES_TO: {etl_name}_{suffix}")

        # ── Install write interceptor ──
        spark = getattr(self, "spark", None)
        write_capture = None
        if spark is not None:
            try:
                from etlnexus_hooks.spark_introspect import capture_writes
                write_capture = capture_writes(spark)
                captured_tables = write_capture.__enter__()
            except Exception:
                write_capture = None
                captured_tables = []
        else:
            captured_tables = []

        # ── Execute ETL: extract → transform → load ──
        try:
            self.extract()
            self.transform()
            self.load()
        except Exception:
            # Clean up write interceptor before re-raising
            if write_capture is not None:
                try:
                    write_capture.__exit__(None, None, None)
                except Exception:
                    pass
            raise

        # ── Post-run: clean up write interceptor ──
        if write_capture is not None:
            try:
                write_capture.__exit__(None, None, None)
            except Exception:
                pass

        # ── Post-run: emit additionally captured writes ──
        already_emitted = {etl_name} | {f"{etl_name}_{s}" for s in suffixes}
        for table in captured_tables:
            from etlnexus_hooks.spark_introspect import parse_table_name
            short_name = parse_table_name(table)
            if short_name not in already_emitted:
                print(f"ETL_WRITES_TO: {short_name}")
                already_emitted.add(short_name)

        if spark is None:
            return

        # ── Post-run: emit resource metrics ──
        try:
            from etlnexus_hooks.spark_introspect import collect_metrics
            metrics = collect_metrics(spark)
            if metrics:
                print(f"ETL_RESOURCE_ACTUAL: {json.dumps(metrics)}")
        except Exception:
            logger.debug("Could not collect metrics for %s", etl_name, exc_info=True)

        # ── Post-run: emit execution plan ──
        try:
            from etlnexus_hooks.spark_introspect import extract_execution_plan
            result_df = getattr(self, "result", None)
            plan = extract_execution_plan(spark, result_df)
            if plan:
                print(f"ETL_EXECUTION_PLAN: {json.dumps(plan)}")
        except Exception:
            logger.debug("Could not extract execution plan for %s", etl_name, exc_info=True)


def etlnexus_instrument(cls):
    """Class decorator that adds EtlNexusMixin to an existing ETL class.

    Use when you cannot change BaseETL's inheritance::

        @etlnexus_instrument
        class MyETL(BaseETL):
            ...

    This dynamically inserts ``EtlNexusMixin`` into the class's MRO.
    """
    if EtlNexusMixin not in cls.__mro__:
        cls.__bases__ = (EtlNexusMixin,) + cls.__bases__
    return cls


# ── Internal helpers ──────────────────────────────────────────────────

def _get_etl_description(cls: type) -> str:
    """Get the ETL description — defaults to the relative file path of the class.

    Returns a path like ``dagger/PortScanCollector.py`` relative to the
    nearest team directory, or the full path if the structure is unknown.
    """
    try:
        source_file = inspect.getfile(cls)
        path = Path(source_file)

        # Try to make a short relative path: team/ClassName.py
        # Walk up looking for a parent that looks like a team directory
        parts = path.parts
        for i in range(len(parts) - 1, 0, -1):
            parent_name = parts[i - 1]
            # Skip generic directories
            if parent_name in ("src", "lib", "site-packages", "__pycache__"):
                continue
            # Return parent/filename
            return f"{parent_name}/{path.name}"

        return path.name
    except (TypeError, OSError):
        return cls.__name__


def _get_module_suffixes(cls: type) -> list[str]:
    """Extract the module-level SUFFIXES list from the ETL class's module."""
    try:
        module = sys.modules.get(cls.__module__)
        if module is not None:
            suffixes = getattr(module, "SUFFIXES", None)
            if isinstance(suffixes, (list, tuple)):
                return list(suffixes)
    except Exception:
        pass
    return []
