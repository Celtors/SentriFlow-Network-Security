import asyncio
import contextlib
import json
import os
import secrets
from pathlib import Path

import psutil
import uvicorn

from sentriflow.api.server import create_app
from sentriflow.config import Config
from sentriflow.intel.blocklist_loader import parse_domains
from sentriflow.os_adapters.windows.file_acl import restrict_directory
from sentriflow.proxy.runner import create_master
from sentriflow.runtime import Runtime


def acquire_session(data_dir: Path) -> Path:
    lock = data_dir / "session.lock"
    if lock.exists():
        previous = json.loads(lock.read_text(encoding="utf-8"))
        try:
            process = psutil.Process(previous["pid"])
            if abs(process.create_time() - previous["created"]) < 0.01:
                raise RuntimeError("Another SentriFlow instance is using this data directory")
        except psutil.Error:
            pass
        lock.unlink()
    with lock.open("x", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "created": psutil.Process().create_time()}, stream)
    return lock


async def run(config: Config, import_path: Path | None = None) -> None:
    restrict_directory(config.data_dir)
    lock = acquire_session(config.data_dir)
    runtime = None
    master = None
    tasks: list[asyncio.Task] = []
    try:
        runtime = Runtime(config)
        if import_path:
            domains, skipped = parse_domains(import_path.read_text(encoding="utf-8"))
            runtime.blocklist.add(domains, import_path.name)
            print(f"Imported {len(domains)} domains; unsupported entries skipped: {skipped}")
        token = secrets.token_urlsafe(32)
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(runtime, token),
                host="127.0.0.1",
                port=config.api_port,
                access_log=False,
                log_level="warning",
                timeout_graceful_shutdown=2,
            )
        )
        if not config.api_only:
            master = create_master(runtime)
        print(f"Dashboard: http://127.0.0.1:{config.api_port}", flush=True)
        print(f"Session token: {token}", flush=True)
        print(
            f"Proxy: 127.0.0.1:{config.proxy_port}; explicit routing or opt-in Settings toggle.",
            flush=True,
        )
        print(f"Local data: {config.data_dir.resolve()}", flush=True)
        if runtime.system_proxy.journal.exists():
            print("A proxy recovery journal exists. Check doctor / restore-proxy before routing.")
        tasks = [asyncio.create_task(server.serve()), asyncio.create_task(runtime.ticker())]
        if master:
            tasks.append(asyncio.create_task(master.run()))
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        if runtime:
            runtime.halts.shutdown()
            await asyncio.sleep(0)
            try:
                runtime.system_proxy.restore()
            except (RuntimeError, OSError):
                print("Proxy could not be restored automatically; recovery journal preserved.")
        if master:
            master.shutdown()
        if "server" in locals():
            server.should_exit = True
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 4)
        except TimeoutError:
            for task in tasks:
                task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        if runtime:
            runtime.geoip.close()
            runtime.db.close()
        lock.unlink(missing_ok=True)
