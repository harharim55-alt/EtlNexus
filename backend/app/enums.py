"""Domain enumerations for EtlNexus.

Using ``StrEnum`` so that enum members are equal to their string values and
can be used directly in comparisons, Pydantic schemas, and SQLAlchemy
string columns without extra casting.
"""

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class GrantLevel(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"


class PipelineType(StrEnum):
    ETL = "etl"
    API = "api"
