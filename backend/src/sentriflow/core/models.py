"""Domain models. No dependency on transport, proxy, or operating-system adapters."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def identifier() -> str:
    return str(uuid4())


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Verdict(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    HALT = "halt"


class ProcessInfo(Model):
    pid: int | None = None
    name: str = "Unknown"
    key: str | None = None


class Finding(Model):
    label: str
    location: str
    type: Literal["pii", "tracker", "large_upload", "inspection", "anomaly"] = "pii"
    masked_sample: str = "[redacted]"


class Flow(Model):
    id: str = Field(default_factory=identifier)
    ts: str = Field(default_factory=utcnow)
    updated_at: str = Field(default_factory=utcnow)
    pid: int | None = None
    process_name: str = "Unknown"
    process_key: str | None = None
    method: str = "GET"
    scheme: str = "http"
    host: str
    port: int = 80
    path_masked: str = "[omitted]"
    bytes_up: int = 0
    bytes_down: int = 0
    tls_status: Literal["inspected", "not_inspected", "passthrough"] = "inspected"
    verdict: Verdict = Verdict.ALLOW
    verdict_source: str = "default"
    state: Literal["started", "held", "completed", "error"] = "started"
    reason: str = "No risk detected"
    findings: list[Finding] = Field(default_factory=list)
    deadline: str | None = None
    status_code: int | None = None
    country_code: str | None = None
    destination_ip: str | None = None


class Decision(Model):
    action: Literal["allow", "block"]
    scope: Literal["once", "always"] = "once"


class RuleInput(Model):
    process_match: str = Field(pattern=r"^[a-f0-9]{64}$")
    process_name: str = Field(default="Application", min_length=1, max_length=128)
    host_match: str = Field(min_length=1, max_length=253)
    action: Literal["allow", "block"]
    note: str = Field(default="", max_length=200)


class Rule(RuleInput):
    id: str = Field(default_factory=identifier)
    created_at: str = Field(default_factory=utcnow)


class PatternInput(Model):
    label: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9 _-]+$")
    pattern: str = Field(min_length=1, max_length=256)
    is_regex: bool = False
    enabled: bool = True

    @field_validator("pattern")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Sensitive strings cannot be blank")
        return value


class Pattern(PatternInput):
    id: str = Field(default_factory=identifier)


class Settings(Model):
    inspection_enabled: bool = True
    halt_timeout_seconds: int = Field(default=30, ge=2, le=120)
    unknown_large_bytes: int = Field(default=1_000_000, ge=1024, le=8_000_000)
    tracker_mode: Literal["halt", "block"] = "halt"


class Evaluation(Model):
    verdict: Verdict
    source: str
    reason: str
