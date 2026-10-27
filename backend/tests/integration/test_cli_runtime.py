import asyncio
import os
import sys
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from sentriflow.verification import free_port


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows console termination needs manual acceptance"
)
@pytest.mark.parametrize("api_only,via_env", [(True, False), (False, False), (True, True)])
async def test_cli_starts_listeners_and_shuts_down(tmp_path, api_only, via_env):
    api_port, proxy_port = free_port(), free_port()
    while proxy_port == api_port:
        proxy_port = free_port()
    arguments = [sys.executable, "-I", "-m", "sentriflow", "run", "--data-dir", str(tmp_path)]
    if api_only and not via_env:
        arguments.append("--api-only")
    if via_env:
        source = tmp_path / "imported-hosts.txt"
        source.write_text("0.0.0.0 tracker.example.test\n")
        arguments.extend(["--import-blocklist", str(source)])
    process = await asyncio.create_subprocess_exec(
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            **os.environ,
            "SENTRIFLOW_API_PORT": str(api_port),
            "SENTRIFLOW_PROXY_PORT": str(proxy_port),
            "SENTRIFLOW_API_ONLY": "true" if via_env else "false",
        },
    )
    try:
        async with asyncio.timeout(10):
            while True:
                line = await process.stdout.readline()
                if line.startswith(b"Dashboard: ") or not line:
                    break
        assert line.startswith(b"Dashboard: ")
        url = line.decode().strip().removeprefix("Dashboard: ")
        token = parse_qs(urlsplit(url).fragment)["token"][0]
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(
                f"http://127.0.0.1:{api_port}/api/health", headers={"X-SentriFlow-Token": token}
            )
            if via_env:
                status = await client.get(
                    f"http://127.0.0.1:{api_port}/api/blocklist/status",
                    headers={"X-SentriFlow-Token": token},
                )
                assert any(
                    row["source"] == "imported-hosts.txt" and row["count"] == 1
                    for row in status.json()["sources"]
                )
        assert response.status_code == 200
        assert response.json()["proxy_running"] is (not api_only)
        assert not (tmp_path / "state.json").exists()
    finally:
        if process.returncode is None:
            process.terminate()
        _, stderr = await asyncio.wait_for(process.communicate(), 8)
    assert b"Traceback" not in stderr
    assert not (tmp_path / "session.lock").exists()
