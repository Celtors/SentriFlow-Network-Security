from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sentriflow.api.server import create_app
from sentriflow.application import Runtime
from sentriflow.config import Settings


@pytest.fixture
def runtime(tmp_path: Path) -> Runtime:
    return Runtime(Settings(data_dir=tmp_path, halt_timeout_seconds=0.2))


@pytest.fixture
def client(runtime: Runtime):
    with TestClient(
        create_app(runtime),
        base_url="http://127.0.0.1:8787",
        headers={"X-SentriFlow-Token": runtime.token},
    ) as client:
        yield client
