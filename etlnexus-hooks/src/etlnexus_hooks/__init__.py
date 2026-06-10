"""EtlNexus Hooks — auto-instrumentation for BaseETL subclasses.

Add the mixin to your BaseETL to automatically emit all structured log
markers that EtlNexus reads from Airflow task logs:

    from etlnexus_hooks import EtlNexusMixin

    class BaseETL(EtlNexusMixin):
        ...  # everything else unchanged

Or use the decorator on individual ETL classes:

    from etlnexus_hooks import etlnexus_instrument

    @etlnexus_instrument
    class MyETL(BaseETL):
        ...
"""

from etlnexus_hooks.mixin import EtlNexusMixin, etlnexus_instrument

__all__ = ["EtlNexusMixin", "etlnexus_instrument"]
