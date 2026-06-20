from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Shared secret for inbound events from MetricGraph + ingest_engine.
    hub_webhook_secret: str = ""

    # MetricGraph REST API (inbound chat actions + Linear registry lookups).
    metricgraph_base_url: str = "http://localhost:8000"
    margin_api_key: str = ""
    openrouter_api_key: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_alert_channel: str = ""
    slack_info_channel: str = ""
    slack_ingest_channel: str = ""

    # Microsoft Teams
    teams_incoming_webhook_url: str = ""
    teams_outgoing_webhook_secret: str = ""

    # Linear
    linear_api_key: str = ""
    linear_webhook_secret: str = ""
    linear_team_id: str = ""
    linear_bot_user_id: str = ""

    # Service
    state_db: str = "./.hub_state.db"
    hub_config_file: str = "config.yaml"
    log_level: str = "INFO"


settings = Settings()
