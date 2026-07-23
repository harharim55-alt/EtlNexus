from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    db_echo: bool = False
    db_command_timeout: int = 30  # asyncpg query timeout in seconds
    # asyncpg prepared-statement cache size. Set to 0 when connecting through a
    # TRANSACTION-pooling PgBouncer (named prepared statements don't survive across
    # pooled server connections). Default 100 = asyncpg's default.
    db_statement_cache_size: int = 100
    # Whether to attempt CREATE DATABASE on startup. Set false when connecting to an
    # EXISTING/managed database (it must already exist) — the app then skips connecting
    # to the maintenance `postgres` DB and only creates its own schema + tables. Avoids
    # errors on managed PG / poolers that don't expose the `postgres` database.
    db_create_database: bool = True
    # Postgres schema for the app's OWN tables. They are created here and every query
    # against them is schema-qualified (e.g. "<db_schema>.ui_catalog_data_products").
    # No connection search_path is set, so this works through poolers like PgBouncer.
    # Use this when the target DB keeps the app in a dedicated schema, not "public".
    db_schema: str = "public"

    # Spark Connect (Iceberg catalog access)
    spark_connect_url: str = "sc://spark-connect:15002"
    spark_catalog_name: str = "spark_catalog"  # Spark catalog holding the tables (fqn: <catalog>.<ns>.<table>)

    # External, read-only table that lists which Iceberg tables exist. Provided by
    # an outside system — the app only reads its `db_name` (namespace) and
    # `tbl_name` (table) columns and never creates or writes it.
    iceberg_metrics_table: str = "iceberg_table_metrics"
    # Schema the external iceberg_table_metrics table lives in. Empty = default to
    # DB_SCHEMA (or public when DB_SCHEMA is public). Set this only when the external
    # table sits in a different schema than the app's own tables (e.g. it's in public
    # while the app runs in a dedicated schema -> set this to "public").
    iceberg_metrics_schema: str = ""
    # Only list tables whose iceberg_table_metrics `date` column equals (today - N days),
    # evaluated DB-side via CURRENT_DATE. 1 = yesterday's snapshot (the default), 0 = today.
    iceberg_metrics_day_offset: int = 1
    # TTL (seconds) for the process-local cache of a single table's live schema,
    # so repeated views don't hammer Spark Connect.
    table_schema_cache_ttl: int = 60

    # Consume-snippet templates (Python str.format fields; use literal "\n" for
    # newlines when overriding via .env — it is unescaped).
    #   table   placeholders: {namespace} (catalog namespace), {table} (table name)
    #   product placeholder:  {product} (data product name, normalised)
    consume_snippet_table_template: str = (
        "from etls import Catalog, Engine\n\n"
        'Catalog(Engine.Spark).iceberg.{namespace}.{table}("date").consume().as_pyspark()'
    )
    consume_snippet_product_template: str = (
        'from etls import Catalog, Engine\n\nCatalog(Engine.Spark).read_by_tag.{product}("date").consume().as_pyspark()'
    )

    # AI / LLM
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "default"
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 30.0
    llm_verify_ssl: bool = False  # verify the LLM endpoint's TLS cert (off for internal/self-signed)
    # First message the AI Architect chat shows before the user types anything.
    ai_greeting: str = (
        "Hello! I am your AI Data Architect. You can ask me about the existing data "
        "products or look for a data product that matches your needs. Where would you "
        "like to start?"
    )
    # How long the browser waits for an AI chat reply before giving up. The chat is a
    # single long-blocking request (the backend buffers the whole LLM stream), so this
    # must comfortably exceed a slow LLM's total response time. Delivered to the SPA via
    # /api/auth/config. Keep <= the frontend nginx API_PROXY_READ_TIMEOUT.
    ai_request_timeout_seconds: int = 300

    # App
    cors_origins: list[str] = ["http://localhost:5173"]
    debug: bool = False
    log_format: str = "auto"  # "json", "text", or "auto" (json unless debug)
    deployment_env: str = "development"  # "development", "staging", "production"
    # Branding shown on the login page (delivered to the SPA via /api/auth/config).
    # app_owner renders as the "Made by …" credit; leave empty to hide it.
    app_name: str = "ETL Nexus"
    app_owner: str = ""
    trusted_proxy_depth: int = 1  # Trusted reverse proxy hops; 0 = ignore X-Forwarded-For
    max_request_body_bytes: int = 1_048_576  # Reject requests with a larger Content-Length
    rate_limit_default: str = "200/minute"  # Global per-client request rate limit
    rate_limit_ai: str = "60/minute"  # Rate limit for the AI Architect endpoint

    # OIDC HTTP client / JWKS
    oidc_http_timeout_seconds: float = 10.0
    jwks_cache_ttl_seconds: int = 6 * 3600
    # TLS to the IdP (the backend fetches .well-known + JWKS over HTTPS).
    #   oidc_verify_ssl=False -> skip cert verification entirely (insecure; testing only).
    #                            OIDC_CA_BUNDLE is ignored in this mode.
    #   oidc_verify_ssl=True  -> verify. If oidc_ca_bundle is set, use it as the trust
    #                            store (for a private/internal CA); otherwise system/certifi CAs.
    oidc_verify_ssl: bool = True
    oidc_ca_bundle: str = ""

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
    # Rename SSO groups to the team names used in the app. Keys = the group name as it
    # appears in the token (matched with OR without a leading "/"); values = the system
    # team name. Unmapped groups pass through unchanged. JSON dict in env, e.g.
    # SSO_GROUP_MAP={"kc-dagger-team":"Dagger","/vault-grp":"Vault"}
    sso_group_map: dict[str, str] = {}
    sso_public_issuer_url: str = "http://localhost:8090/realms/etlnexus"
    # Secret for a CONFIDENTIAL Keycloak client. The SPA runs the OIDC flow, so this
    # is delivered to the browser (via /api/auth/config) and sent by oidc-client-ts on
    # the token exchange. Leave empty for a public client. SECURITY: a confidential
    # secret exposed to the browser gives no real protection over a public client —
    # only set this when your IdP mandates a confidential client for an internal app.
    sso_client_secret: str = ""

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


def _normalize_ident(value: str) -> str:
    """Normalise a name into a catalog identifier (lowercase, spaces->_, strip Dummy)."""
    norm = value.replace(" ", "_").lower()
    if norm.endswith("dummy"):
        norm = norm[: -len("dummy")]
    return norm


def render_table_consume_snippet(namespace: str, table_name: str) -> str:
    """Render the per-table consume snippet (iceberg.<namespace>.<table>) from the env template."""
    template = settings.consume_snippet_table_template.replace("\\n", "\n")
    try:
        return template.format(namespace=namespace.lower(), table=_normalize_ident(table_name))
    except (KeyError, IndexError, ValueError):
        return template


def render_product_consume_snippet(name: str) -> str:
    """Render the product-level consume snippet (read_by_tag.<product>) from the env template."""
    template = settings.consume_snippet_product_template.replace("\\n", "\n")
    try:
        return template.format(product=_normalize_ident(name))
    except (KeyError, IndexError, ValueError):
        return template
