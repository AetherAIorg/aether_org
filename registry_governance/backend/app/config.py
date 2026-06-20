from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://catalog:catalog@localhost:5433/catalog"
    metricgraph_base_url: str = "http://localhost:8000"
    registry_base_url: str = "http://localhost:3000"
    webhook_secret: str = ""
    # Optional: trigger KG materialize in MetricGraph after governance sync events
    metricgraph_materialize_url: str = ""
    metricgraph_api_key: str = ""
    cors_origins: str = "http://localhost:3001"
    auto_sync_on_startup: bool = True


settings = Settings()
