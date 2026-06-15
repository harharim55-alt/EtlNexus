from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    db_echo: bool = False
    db_command_timeout: int = 30  # asyncpg query timeout in seconds

    # Spark Connect (Iceberg catalog access)
    spark_connect_url: str = "sc://spark-connect:15002"
    spark_catalog_name: str = "iceberg"  # Spark catalog alias holding the Iceberg tables
    spark_namespace_prefix: str = "dagger,prism,vault,oasis"

    # Consume-snippet templates. The default "Import & Consume" snippet shown for a
    # product / tag is rendered from these. Placeholders (Python str.format fields):
    #   {namespace} = team name lowercased (catalog namespace)
    #   {name}      = product name normalised (lowercase, spaces→_)
    #   {team}      = raw team name lowercased
    #   {tag}       = tag name normalised (tags only)
    # Use a literal "\n" for newlines when overriding via .env (it is unescaped).
    consume_snippet_template: str = (
        'from etls import Catalog, Engine\n\n'
        'Catalog(Engine.Spark).iceberg.{namespace}.{name}("date").consume().as_pyspark()'
    )
    consume_snippet_tag_template: str = (
        'from etls import Catalog, Engine\n\n'
        'Catalog(Engine.Spark).read_by_tag.{tag}("date").consume().as_pyspark()'
    )
    # How often the backend polls Spark Connect and refreshes the Postgres catalog
    # mirror (catalog_columns). End-user reads hit Postgres, never Spark live.
    catalog_mirror_interval_seconds: int = 30
    # Max time to wait for a Spark Connect catalog read before abandoning the
    # refresh. Must be < interval so a hung Spark server can't stall all refreshes.
    catalog_mirror_spark_timeout_seconds: int = 25

    # AI / LLM
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "default"
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 30.0

    # App
    cors_origins: list[str] = ["http://localhost:5173"]
    debug: bool = False
    log_format: str = "auto"  # "json", "text", or "auto" (json unless debug)
    scheduler_enabled: bool = True  # Set to false for API-only mode (no background tasks)
    deployment_env: str = "development"  # "development", "staging", "production"
    trusted_proxy_depth: int = 1  # Trusted reverse proxy hops; 0 = ignore X-Forwarded-For
    max_request_body_bytes: int = 1_048_576  # Reject requests with a larger Content-Length
    rate_limit_default: str = "200/minute"  # Global per-client request rate limit
    rate_limit_ai: str = "60/minute"  # Rate limit for the AI Architect endpoint

    # OIDC HTTP client / JWKS
    oidc_http_timeout_seconds: float = 10.0
    jwks_cache_ttl_seconds: int = 6 * 3600

    # Cache TTLs (seconds) and page limits
    cache_ttl_short: int = 30
    cache_ttl_medium: int = 60
    default_page_limit: int = 200
    default_page_limit_small: int = 20

    # Master admins (superusers). Comma-separated usernames (Keycloak
    # preferred_username). These users can edit every product across all teams
    # and manage any team's membership — everything a team-leader admin can do,
    # for all teams. Roles themselves still come from Keycloak.
    master_admin_usernames: str = ""

    # Teams that may exist in the system, sourced from Keycloak groups. Either an
    # explicit allow-list (e.g. ["Dagger","Vault"]) — only these Keycloak groups
    # become teams and they are pre-created at startup — or ["*"] to allow every
    # group Keycloak presents (teams created on-demand at login, none pre-created).
    system_teams: list[str] = ["*"]

    # SSO / OIDC
    sso_enabled: bool = False
    sso_issuer_url: str = "http://keycloak:8090/realms/etlnexus"
    sso_client_id: str = "etlnexus-app"
    sso_audience: str = "etlnexus-app"
    sso_groups_claim: str = "groups"
    sso_role_claim: str = "realm_access.roles"
    sso_admin_role: str = "admin"
    sso_public_issuer_url: str = "http://localhost:8090/realms/etlnexus"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


def is_master_admin(username: str | None) -> bool:
    """Return whether the given username is configured as a master admin (superuser)."""
    if not username:
        return False
    masters = {m.strip().lower() for m in settings.master_admin_usernames.split(",") if m.strip()}
    return username.lower() in masters


def team_is_allowed(name: str | None) -> bool:
    """Whether a team name is permitted by SYSTEM_TEAMS (``["*"]`` allows all)."""
    if not name:
        return False
    allowed = settings.system_teams
    if not allowed or "*" in allowed:
        return True
    return name.strip().lower() in {t.strip().lower() for t in allowed}


def configured_team_names() -> list[str]:
    """Explicit team allow-list (empty when SYSTEM_TEAMS is the ``["*"]`` wildcard)."""
    allowed = settings.system_teams
    if not allowed or "*" in allowed:
        return []
    return [t.strip() for t in allowed if t.strip()]


def render_consume_snippet(name: str, team: str | None, is_tag: bool) -> str:
    """Render the default consume snippet for a product/tag from the env template."""
    norm = name.replace(" ", "_").lower()
    if norm.endswith("dummy"):
        norm = norm[: -len("dummy")]
    team_l = (team or "").lower()
    namespace = team_l or "dagger"
    template = settings.consume_snippet_tag_template if is_tag else settings.consume_snippet_template
    template = template.replace("\\n", "\n")
    try:
        return template.format(namespace=namespace, name=norm, team=team_l, tag=norm)
    except (KeyError, IndexError, ValueError):
        # Malformed template (unknown placeholder / stray brace) — return as-is.
        return template
