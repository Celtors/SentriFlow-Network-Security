from typing import Literal

from pydantic import Field, field_validator, model_validator

from sentriflow.core.models import Model
from sentriflow.core.rule_engine import normalize_host


class DecisionInput(Model):
    action: Literal["allow", "block"]
    scope: Literal["once", "always"] = "once"


class RuleInput(Model):
    process_match: str | None = Field(default=None, min_length=1, max_length=512)
    host_match: str | None = Field(default=None, min_length=1, max_length=253)
    action: Literal["allow", "block"]
    note: str = Field(default="", max_length=500)

    @field_validator("host_match")
    @classmethod
    def valid_host(cls, value: str | None) -> str | None:
        if value is None:
            return value
        wildcard = value.startswith("*.")
        host = normalize_host(value[2:] if wildcard else value)
        if not host or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789.-:" for c in host):
            raise ValueError("Use a hostname, IP address, or *.domain wildcard")
        return ("*." if wildcard else "") + host

    @model_validator(mode="after")
    def has_target(self) -> "RuleInput":
        if not self.process_match and not self.host_match:
            raise ValueError("A rule needs a process or host")
        return self


class SettingsInput(Model):
    inspection_enabled: bool | None = None
    halt_timeout_seconds: float | None = Field(default=None, ge=0.05, le=300)
    large_upload_bytes: int | None = Field(default=None, ge=1, le=1_073_741_824)
    tracker_policy: Literal["ask", "block", "alert"] | None = None


class ProxyInput(Model):
    enabled: bool


class ConsentInput(Model):
    confirmed: Literal[True]


class HaltCommandData(DecisionInput):
    id: str


class HaltCommand(Model):
    type: Literal["halt.decide"]
    data: HaltCommandData
