import asyncio
import contextlib
import sys

import uvicorn
from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster

from sentriflow.api.server import create_app
from sentriflow.application import Runtime
from sentriflow.config import Settings
from sentriflow.constants import LOOPBACK
from sentriflow.logging_setup import configure_logging
from sentriflow.os_adapters.windows.cert_store import prepare_ca
from sentriflow.os_adapters.windows.file_acl import restrict_private_directory
from sentriflow.os_adapters.windows.system_proxy import SystemProxy
from sentriflow.proxy.addon import SentriFlowAddon


def create_master(runtime: Runtime) -> DumpMaster:
    config = runtime.config
    opts = options.Options(
        listen_host=LOOPBACK, listen_port=config.proxy_port, confdir=str(config.ca_dir)
    )
    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    # Additional options are registered by DumpMaster's default addons.
    opts.update(body_size_limit="2m", connection_strategy="lazy")
    master.addons.add(SentriFlowAddon(runtime))
    return master


async def run(config: Settings, *, system_proxy: bool = False, api_only: bool = False) -> None:
    if system_proxy and (sys.platform != "win32" or api_only):
        raise ValueError("System routing requires Windows and the local proxy")
    restrict_private_directory(config.data_dir)
    configure_logging(config.data_dir, config.log_level)
    runtime = Runtime(config)
    if sys.platform == "win32":
        runtime.system_proxy = SystemProxy(config.data_dir / "state.json", config.proxy_port)
    master = None
    tasks: list[asyncio.Task] = []
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(runtime),
            host=LOOPBACK,
            port=config.api_port,
            access_log=False,
            log_level="warning",
            ws_max_size=4096,
            timeout_graceful_shutdown=3,
        )
    )
    try:
        await runtime.open()
        if not api_only:
            await asyncio.to_thread(prepare_ca, config.ca_dir)
            master = create_master(runtime)
            tasks.append(asyncio.create_task(master.run()))
        tasks.append(asyncio.create_task(server.serve()))
        tasks.append(asyncio.create_task(runtime.speed_ticker()))
        # Do not change system routing until both listening services report ready.
        for _ in range(200):
            if any(task.done() for task in tasks):
                for task in tasks:
                    if task.done():
                        task.result()
                raise RuntimeError("A service stopped during startup")
            if server.started and (master is None or runtime.proxy_running):
                break
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("Timed out starting local services")
        runtime.proxy_running = master is not None
        if system_proxy:
            await asyncio.to_thread(runtime.system_proxy.enable)
        print(f"Dashboard: http://{LOOPBACK}:{config.api_port}/#token={runtime.token}", flush=True)
        print(
            "Session token is in the URL fragment; use it as X-SentriFlow-Token for REST.",
            flush=True,
        )
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in tasks:
            if task.done():
                task.result()
    finally:
        runtime.halts.shutdown()
        # Restoration precedes stopping the listener, including on partial startup failure.
        try:
            if runtime.system_proxy and runtime.system_proxy.enabled:
                await asyncio.to_thread(runtime.system_proxy.restore)
        finally:
            runtime.proxy_running = False
            if master:
                master.shutdown()
            server.should_exit = True
            for task in tasks:
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.gather(*tasks, return_exceptions=True)
            await runtime.close()
