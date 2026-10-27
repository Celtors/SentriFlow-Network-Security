from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from sentriflow.constants import API_PORT, PROXY_PORT
from sentriflow.os_adapters.windows.paths import data_directory


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTRIFLOW_", extra="ignore")

    api_port: int = Field(default=API_PORT, ge=1024, le=65535)
    proxy_port: int = Field(default=PROXY_PORT, ge=1024, le=65535)
    data_dir: Path = Field(default_factory=data_directory)
    halt_timeout_seconds: float = Field(default=30, ge=0.05, le=300)
    large_upload_bytes: int = Field(default=1_048_576, ge=1)
    inspection_enabled: bool = True
    tracker_policy: Literal["ask", "block", "alert"] = "ask"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    frontend_dir: Path = Field(default_factory=lambda: Path(__file__).parent / "web")
    geoip_database: Path = Field(
        default_factory=lambda: Path(__file__).parent / "data" / "geoip" / "dbip-country-lite.mmdb"
    )

    @model_validator(mode="after")
    def distinct_ports(self) -> "Settings":
        if self.api_port == self.proxy_port:
            raise ValueError("API and proxy ports must differ")
        return self

    @property
    def database_path(self) -> Path:
        return self.data_dir / "sentriflow.db"

    @property
    def ca_dir(self) -> Path:
        return self.data_dir / "ca"


# Both names use the same validated configuration for the R2 runtime and R4 tools.
Config = Settings
