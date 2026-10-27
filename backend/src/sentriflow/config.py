import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTRIFLOW_", extra="ignore")
    proxy_port: int = Field(default=8080, ge=1024, le=65535)
    api_port: int = Field(default=8787, ge=1024, le=65535)
    halt_timeout_seconds: int = Field(default=30, ge=2, le=120)
    data_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SentriFlow"
    )
    frontend_dir: Path = Field(default_factory=lambda: Path(__file__).parent / "web")
    api_only: bool = False
    geoip_database: Path = Field(
        default_factory=lambda: Path(__file__).parent / "data" / "geoip" / "dbip-country-lite.mmdb"
    )
