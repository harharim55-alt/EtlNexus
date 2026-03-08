"""Filter Iceberg namespaces to only those under the dagger prefix."""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def filter_dagger_namespaces(namespaces: list[list[str]]) -> list[str]:
    """Filter namespaces to only those matching the configured prefix.

    The prefix is configured via `iceberg_namespace_prefix` (e.g., "catalog.iceberg.dagger").
    Namespaces can be represented as lists of parts (["catalog", "iceberg", "dagger"])
    or dot-separated strings.
    """
    prefix = settings.iceberg_namespace_prefix
    prefix_parts = prefix.split(".")
    matched = []

    for ns in namespaces:
        # Normalize: namespace might be a list of parts or a single string
        if isinstance(ns, list):
            ns_parts = ns
        elif isinstance(ns, str):
            ns_parts = ns.split(".")
        else:
            continue

        if len(ns_parts) >= len(prefix_parts) and ns_parts[: len(prefix_parts)] == prefix_parts:
            matched.append(".".join(ns_parts))

    logger.info(
        "Filtered %d namespaces to %d matching prefix '%s'",
        len(namespaces), len(matched), prefix,
    )
    return matched
