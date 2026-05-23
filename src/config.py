"""Configuration settings for the Tournament Management System."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database settings
    db_user: str = "tournament"
    db_password: str = "tournament_password"
    db_name: str = "tournament_db"
    db_host: str = "localhost"
    db_port: int = 5432

    @property
    def database_url(self) -> str:
        """Construct asyncpg database URL."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Construct synchronous psycopg2 database URL (for Alembic)."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # Application settings
    app_port: int = 8000
    api_key_secret: str = "super_secret_key_change_in_production"

    # Environment settings
    environment: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
