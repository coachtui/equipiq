from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    database_url: str = "postgresql://fix:fix@localhost:5432/fixdb"
    environment: str = "development"

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # File uploads
    upload_dir: str = "/app/uploads"
    max_file_size_mb: int = 20

    # Diagnostic engine
    max_turns: int = 10
    early_exit_confidence: float = 0.75
    early_exit_lead: float = 0.20  # top hypothesis must lead second by this margin

    # Rate limiting (requests per minute per IP)
    rate_limit_session_create: str = "10/minute"
    rate_limit_session_message: str = "30/minute"
    rate_limit_session_image: str = "5/minute"
    rate_limit_obd_lookup: str = "20/minute"
    rate_limit_dtc_lookup: str = "20/minute"
    rate_limit_auth: str = "5/minute"

    # Auth / JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"


settings = Settings()
