from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    db_echo: bool = False

    # Airflow Integration
    airflow_base_url: str = "http://airflow-webserver:8080/api/v1"
    airflow_username: str = "admin"
    airflow_password: str = "admin"
    airflow_poll_interval_minutes: int = 20

    # Iceberg Catalog
    iceberg_catalog_uri: str = "http://iceberg-rest:8181"
    iceberg_catalog_name: str = "iceberg"
    iceberg_namespace_prefix: str = "dagger,prism,vault,oasis"

    # AI / LLM
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "default"
    llm_max_tokens: int = 1024

    # App
    cors_origins: list[str] = ["http://localhost:5173"]
    debug: bool = False
    log_format: str = "auto"  # "json", "text", or "auto" (json unless debug)

    # Tuning
    airflow_semaphore_limit: int = 6
    airflow_startup_max_attempts: int = 20
    airflow_startup_retry_seconds: int = 15

    # Spark Cluster Capacity (for resource utilization display)
    spark_max_driver_memory_gb: int = 16
    spark_max_executor_memory_gb: int = 64
    spark_max_executor_cores: int = 32
    spark_max_total_executors: int = 20

    # Airflow Auto-Discovery
    airflow_exclude_operator_types: str = "EmptyOperator,DummyOperator,BranchPythonOperator,TriggerDagRunOperator,ShortCircuitOperator"
    infer_lineage_from_dag_graph: bool = False  # Infer reads_from edges from DAG task dependencies

    # Cache TTLs (seconds) and page limits
    cache_ttl_short: int = 30
    cache_ttl_medium: int = 60
    cache_ttl_airflow: int = 300
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
