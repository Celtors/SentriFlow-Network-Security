"""Public contracts. Request bodies and raw headers never enter these models."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Verdict(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    HALT = "halt"


class Finding(Model):
    type: str
    label: str
    severity: str = "high"
    masked_sample: str = "[redacted]"
    location: str = "body"


class ProcessInfo(Model):
    pid: int | None = None
    name: str = "Unknown"
    exe_path: str | None = None
    key: str | None = None


class Flow(Model):
    id: str = Field(default_factory=new_id)
    ts: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    pid: int | None = None
    process_name: str = "Unknown"
    exe_path: str | None = None
    process_key: str | None = None
    method: str = "GET"
    scheme: str = "http"
    host: str
    port: int = 80
    path_masked: str = "/"
    bytes_up: int = 0
    bytes_down: int = 0
    tls_status: str = "passthrough"
    verdict: Verdict = Verdict.ALLOW
    verdict_source: str = "default"
    matched_rule_id: str | None = None
    country_code: str | None = None
    destination_ip: str | None = None
    state: Literal["started", "held", "completed", "error"] = "started"
    reason: str = "No risk detected"
    deadline: datetime | None = None
    status_code: int | None = None
    findings: list[Finding] = Field(default_factory=list)


class Rule(Model):
    id: str = Field(default_factory=new_id)
    created_at: datetime = Field(default_factory=utc_now)
    process_match: str | None = Field(default=None, max_length=512)
    process_name: str | None = Field(default=None, max_length=512)
    host_match: str | None = Field(default=None, max_length=253)
    action: Verdict
    note: str = Field(default="", max_length=500)


class Decision(Model):
    action: Verdict
    source: str
    rule_id: str | None = None


class Halt(Model):
    id: str
    flow: Flow
    deadline: datetime


class Alert(Model):
    id: str = Field(default_factory=new_id)
    flow_id: str
    ts: datetime = Field(default_factory=utc_now)
    type: str
    severity: str
    pattern_label: str
    masked_sample: str


class CustomPattern(Model):
    id: str = Field(default_factory=new_id)
    label: str = Field(min_length=1, max_length=100)
    pattern: str = Field(min_length=1, max_length=256)
    is_regex: bool = False
    enabled: bool = True
