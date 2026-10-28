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

    # Password Reset settings (Hito 6 - AUTH-03)
    reset_token_secret_key: str = "DIFFERENT_SECRET_FOR_RESET_TOKENS_MIN_32_CHARS"
    reset_token_expire_minutes: int = 30

    # Email Service (Resend)
    resend_api_key: str = ""
    email_from: str = "onboarding@resend.dev"
    frontend_url: str = "http://localhost:3000"

    # Supabase Database for Inventory (Dual Database Architecture)
    supabase_database_url: str = "postgresql://postgres:password@localhost:5432/brasaland_inventory"

    class Config:
        env_file = ".env"


settings = Settings()
