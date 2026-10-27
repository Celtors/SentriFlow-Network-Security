import logging
from unittest.mock import AsyncMock, Mock

import pytest
from mitmproxy import connection, http

from sentriflow.core.models import ProcessInfo
from sentriflow.proxy import runner
from sentriflow.proxy.addon import ConsoleFlowAddon


@pytest.mark.asyncio
@pytest.mark.parametrize("async_resolver", [True, False])
async def test_console_spike_resolves_process_without_logging_request_contents(
    caplog, async_resolver
):
    process = ProcessInfo(pid=1234, name="msedge.exe", exe_path="edge.exe")
    resolver = AsyncMock(return_value=process) if async_resolver else Mock(return_value=process)
    flow = http.HTTPFlow(
        connection.Client(peername=("127.0.0.1", 49152), sockname=("127.0.0.1", 8081)),
        connection.Server(address=("example.test", 80)),
    )
    flow.request = http.Request.make(
        "POST",
        "http://example.test/private-path?token=private-token",
        b"private-body",
        {"X-Private": "private-header"},
    )
    with caplog.at_level(logging.INFO, logger="sentriflow.proxy.spike"):
        await ConsoleFlowAddon(resolver).request(flow)
    resolver.assert_called_once_with(49152)
    assert "host=example.test" in caplog.text
    assert "process=msedge.exe pid=1234" in caplog.text
    assert all(
        value not in caplog.text
        for value in ("private-path", "private-token", "private-body", "private-header")
    )


@pytest.mark.asyncio
async def test_standalone_runner_uses_custom_port_and_shared_ca_directory(monkeypatch, tmp_path):
    opts = Mock()
    options_factory = Mock(return_value=opts)
    master = Mock(run=AsyncMock())
    master_factory = Mock(return_value=master)
    prepare_ca = Mock()
    monkeypatch.setattr(runner.options, "Options", options_factory)
    monkeypatch.setattr(runner, "DumpMaster", master_factory)
    monkeypatch.setattr(runner, "prepare_ca", prepare_ca)
    monkeypatch.setattr(runner, "restrict_private_directory", Mock())

    await runner.serve(port=8081, data_dir=tmp_path)

    options_factory.assert_called_once_with(
        listen_host="127.0.0.1", listen_port=8081, confdir=str(tmp_path / "ca")
    )
    prepare_ca.assert_called_once_with(tmp_path / "ca")
    master_factory.assert_called_once_with(opts, with_termlog=False, with_dumper=False)
    addon = master.addons.add.call_args.args[0]
    assert isinstance(addon, ConsoleFlowAddon)
    assert addon._resolve.__self__.proxy_port == 8081
    master.run.assert_awaited_once()
    master.shutdown.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("host,port", [("0.0.0.0", 8080), ("127.0.0.1", 0), ("127.0.0.1", 65536)])
async def test_standalone_runner_rejects_nonlocal_or_invalid_bind(host, port):
    with pytest.raises(ValueError):
        await runner.serve(host, port)
