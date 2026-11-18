from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings"""
    database_url: str = "sqlite:///./brasaland_ats.db"  # Default to SQLite for development
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS origins - Leer desde environment para producción
    cors_origins: list[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Cargar CORS desde env o usar defaults de desarrollo
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            self.cors_origins = [origin.strip() for origin in cors_env.split(",")]
        else:
            # Defaults para desarrollo local
            self.cors_origins = ["http://localhost:3000", "http://localhost:3001"]

    # JWT Authentication settings (Hito 4)
    # SEGURIDAD: Leer desde environment OBLIGATORIAMENTE
    secret_key: str
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"

    # Password Reset settings (Hito 6 - AUTH-03)
    # SEGURIDAD: Leer desde environment OBLIGATORIAMENTE
    reset_token_secret_key: str
    reset_token_expire_minutes: int = 30

    # Email Service (Resend)
    resend_api_key: str = ""
    email_from: str = "onboarding@resend.dev"
    frontend_url: str = "http://localhost:3000"

    # Supabase Database for Inventory (Dual Database Architecture)
    supabase_database_url: str = "postgresql://postgres:password@localhost:5432/brasaland_inventory"

    class Config:
        env_file = ".env"

    def model_post_init(self, __context) -> None:
        """Validación de seguridad post-inicialización."""
        # Validar que SECRET_KEY no sea el valor por defecto
        if not self.secret_key:
            raise ValueError(
                "SECRET_KEY must be set in environment variables. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Validar que RESET_TOKEN_SECRET_KEY no sea el valor por defecto
        if not self.reset_token_secret_key:
            raise ValueError(
                "RESET_TOKEN_SECRET_KEY must be set in environment variables. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Validar longitud mínima de secretos
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")

        if len(self.reset_token_secret_key) < 32:
            raise ValueError("RESET_TOKEN_SECRET_KEY must be at least 32 characters long")


settings = Settings()
