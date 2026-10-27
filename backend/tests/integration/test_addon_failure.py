from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mitmproxy import connection, http

from sentriflow.core.models import ProcessInfo
from sentriflow.proxy.addon import SentriFlowAddon


@pytest.mark.asyncio
async def test_hook_exception_blocks_and_does_not_log_raw_request(caplog):
    runtime = SimpleNamespace(
        config=SimpleNamespace(api_port=8787),
        resolver=SimpleNamespace(resolve=AsyncMock(return_value=ProcessInfo())),
        inspect=AsyncMock(side_effect=ValueError("private-request-value")),
        locate=lambda *args: None,
    )
    flow = http.HTTPFlow(
        connection.Client(peername=("127.0.0.1", 50000), sockname=("127.0.0.1", 8080)),
        connection.Server(address=("demo.test", 80)),
    )
    flow.request = http.Request.make(
        "POST", "http://demo.test/private-request-value", b"private-request-value"
    )
    await SentriFlowAddon(runtime).request(flow)
    assert flow.response.status_code == 503
    assert flow.metadata["sentriflow"].verdict == "block"
    assert flow.metadata["sentriflow"].verdict_source == "inspection_error"
    assert "private-request-value" not in caplog.text
