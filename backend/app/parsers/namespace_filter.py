"""Filter Spark catalog namespaces to those matching configured team prefixes."""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def filter_namespaces(namespaces: list[list[str]]) -> list[str]:
    """Filter namespaces to only those matching the configured team prefixes.

    The prefixes are configured via `spark_namespace_prefix` as a
    comma-separated list (e.g., "dagger,prism,vault,oasis").
    Namespaces can be represented as lists of parts (["dagger"]) or
    dot-separated strings.
    """
    configured_prefixes = [p.strip() for p in settings.spark_namespace_prefix.split(",")]
    matched = []

    for ns in namespaces:
        # Normalize: namespace might be a list of parts or a single string
        if isinstance(ns, list):
            ns_parts = ns
        elif isinstance(ns, str):
            ns_parts = ns.split(".")
        else:
            continue

        for prefix in configured_prefixes:
            prefix_parts = prefix.split(".")
            if len(ns_parts) >= len(prefix_parts) and ns_parts[: len(prefix_parts)] == prefix_parts:
                matched.append(".".join(ns_parts))
                break

    logger.info(
        "Filtered %d namespaces to %d matching team prefixes %s",
        len(namespaces), len(matched), configured_prefixes,
    )
    return matched
