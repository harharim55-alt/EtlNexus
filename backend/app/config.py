from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus"

    # Airflow Integration
    airflow_base_url: str = "http://airflow-webserver:8080/api/v1"
    airflow_username: str = "admin"
    airflow_password: str = "admin"
    airflow_poll_interval_minutes: int = 20

    # Iceberg Catalog
    iceberg_catalog_uri: str = "http://iceberg-rest:8181"
    iceberg_namespace_prefix: str = "dagger"

    # AI / LLM
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "default"
    llm_max_tokens: int = 1024

    # App
    cors_origins: list[str] = ["http://localhost:5173"]
    debug: bool = False

    # Spark Cluster Capacity (for resource utilization display)
    spark_max_driver_memory_gb: int = 16
    spark_max_executor_memory_gb: int = 64
    spark_max_executor_cores: int = 32
    spark_max_total_executors: int = 20

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
