from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    prometheus_url: str = "http://prometheus:9090"
    database_url: str = "postgresql://postgres:password@postgres:5432/aiops"
    grafana_url: str = "http://grafana:3000"
    slack_webhook_url: str = ""
    pagerduty_routing_key: str = ""
    grafana_api_token: str = ""
    detection_interval_seconds: int = 60
    contamination: float = 0.02

    class Config:
        env_file = ".env"

settings = Settings()
