"""Domain-specific exceptions for EtlNexus.

Use these instead of bare ``except Exception`` to distinguish between
transient errors (retryable) and logic errors (bugs).
"""


class EtlNexusError(Exception):
    """Base exception for all EtlNexus domain errors."""


class AirflowConnectionError(EtlNexusError):
    """Airflow API is unreachable or returned an unexpected error."""


class AirflowSyncError(EtlNexusError):
    """Error during pipeline sync from Airflow."""


class PipelineNotFoundError(EtlNexusError):
    """Requested pipeline does not exist."""


class IcebergCatalogError(EtlNexusError):
    """Error communicating with the Iceberg REST catalog."""


class AuthorizationError(EtlNexusError):
    """User lacks permission for the requested action."""
