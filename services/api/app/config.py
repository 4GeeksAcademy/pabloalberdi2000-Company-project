from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    database_url: str = "sqlite:///./brasaland_ats.db"  # Default to SQLite for development
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # JWT Authentication settings (Hito 4)
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_MIN_32_CHARS"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
