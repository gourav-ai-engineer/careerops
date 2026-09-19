from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CareerOps"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://careerops:change-me-local-only@localhost:5432/careerops"
    smartsheet_access_token: str | None = None
    smartsheet_jobs_sheet_id: int | None = 3084190078947204
    smartsheet_campus_sheet_id: int | None = 156499851825028
    hunter_api_key: str | None = None
    api_key: str | None = None
    frontend_origin: str = "http://localhost:3000"
    http_timeout_seconds: float = 10.0
    provider_requests_per_minute: int = 50
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
