from pydantic import Field

from sentriflow.core.models import Model


class ProxyCommand(Model):
    enabled: bool


class Consent(Model):
    consent: bool = Field(default=False)
