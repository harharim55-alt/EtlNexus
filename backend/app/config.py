from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://etlnexus:etlnexus@db:5432/etlnexus"

    # Git Integration
    git_repo_url: str = "/data/dev-repo"
    git_clone_path: str = "/data/etl-repo"
    git_branch: str = "main"
    git_pull_interval_minutes: int = 60
    git_https_token: str | None = None

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

    # ETL DAGs function
    etl_dags_module: str = "etl_dags"

    # App
    cors_origins: list[str] = ["http://localhost:5173"]
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
