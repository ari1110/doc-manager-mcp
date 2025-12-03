"""Test fixture: Pydantic BaseModel config class."""
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str
    username: str | None = None
    password: str | None = None
    ssl_enabled: bool = False
