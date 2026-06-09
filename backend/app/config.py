from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    db_echo: bool = False
    db_command_timeout: int = 30  # asyncpg query timeout in seconds

    # Spark Connect (Iceberg catalog access — replaces the Iceberg REST catalog)
    spark_connect_url: str = "sc://spark-connect:15002"
    spark_catalog_name: str = "iceberg"  # Spark catalog alias holding the Iceberg tables
    spark_namespace_prefix: str = "dagger,prism,vault,oasis"
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

    # App
    cors_origins: list[str] = ["http://localhost:5173"]
    debug: bool = False
    log_format: str = "auto"  # "json", "text", or "auto" (json unless debug)
    scheduler_enabled: bool = True  # Set to false for API-only mode (no background tasks)
    deployment_env: str = "development"  # "development", "staging", "production"
    trusted_proxy_depth: int = 1  # Trusted reverse proxy hops; 0 = ignore X-Forwarded-For

    # Spark Cluster Capacity (for resource utilization display)
    spark_max_driver_memory_gb: int = 16
    spark_max_executor_memory_gb: int = 64
    spark_max_executor_cores: int = 32
    spark_max_total_executors: int = 20

    # Run history retention
    run_history_retention_days: int = 90  # Delete run history older than this; 0 = keep forever


    # Cache TTLs (seconds) and page limits
    cache_ttl_short: int = 30
    cache_ttl_medium: int = 60
    default_page_limit: int = 200
    default_page_limit_small: int = 20

    # Oasis Prod (external usage metrics database)
    oasis_prod_database_url: str = ""  # Empty = disabled, falls back to seed data
    oasis_prod_username: str = ""
    oasis_prod_password: str = ""
    oasis_prod_pool_size: int = 5
    oasis_prod_max_overflow: int = 3

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
