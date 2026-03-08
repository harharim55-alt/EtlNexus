"""Dynamic import wrapper for get_etl_dags function."""

import importlib
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EtlDagsClient:
    def __init__(self):
        self._module_name = settings.etl_dags_module
        self._loaded = False

    def get_etl_dags(self) -> dict:
        """Dynamically import and call get_etl_dags() from configured module.

        Returns a dict mapping pipeline names to their DAG network names.
        Expected format: {"pipeline_name": ["network1", "network2"]}
        """
        try:
            module = importlib.import_module(self._module_name)
            func = getattr(module, "get_etl_dags", None)
            if func is None:
                logger.warning("Module %s has no get_etl_dags function", self._module_name)
                return {}
            result = func()
            self._loaded = True
            return result if isinstance(result, dict) else {}
        except (ImportError, ModuleNotFoundError):
            logger.info("ETL DAGs module %s not available", self._module_name)
            return {}
        except Exception as e:
            logger.exception("Error calling get_etl_dags: %s", e)
            return {}


etl_dags_client = EtlDagsClient()
