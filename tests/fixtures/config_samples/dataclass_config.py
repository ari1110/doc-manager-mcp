"""Test fixture: Python dataclass config class."""
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    workers: int | None = None
    timeout: float = 30.0
