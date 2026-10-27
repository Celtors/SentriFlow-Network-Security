"""Integrated API/proxy runtime plus R1's standalone Windows feasibility spike."""

import argparse
import asyncio
import contextlib
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster

from sentriflow.api.server import create_app
from sentriflow.application import Runtime
from sentriflow.config import Settings
from sentriflow.constants import LOOPBACK, PROXY_PORT
from sentriflow.logging_setup import configure_logging
from sentriflow.os_adapters.windows.cert_store import prepare_ca
from sentriflow.os_adapters.windows.file_acl import restrict_private_directory
from sentriflow.os_adapters.windows.system_proxy import SystemProxy
from sentriflow.proxy.addon import ConsoleFlowAddon, SentriFlowAddon
from sentriflow.proxy.process_resolver import ProcessResolver

DEFAULT_HOST = LOOPBACK
DEFAULT_PORT = PROXY_PORT


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


async def serve(
    host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *, data_dir: Path | None = None
) -> None:
    """Run R1's console-only spike without starting the API or changing system routing."""
    if host != LOOPBACK:
        raise ValueError("The spike proxy must bind to 127.0.0.1 only")
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    config = Settings(**({"data_dir": data_dir} if data_dir is not None else {}))
    await asyncio.to_thread(restrict_private_directory, config.data_dir)
    await asyncio.to_thread(prepare_ca, config.ca_dir)
    opts = options.Options(listen_host=host, listen_port=port, confdir=str(config.ca_dir))
    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    opts.update(body_size_limit="2m", connection_strategy="lazy")
    master.addons.add(ConsoleFlowAddon(ProcessResolver(proxy_port=port).resolve))
    logging.getLogger("sentriflow.proxy.spike").info(
        "Starting local proxy at http://%s:%d; CA files are in %s", host, port, config.ca_dir
    )
    try:
        await master.run()
    finally:
        master.shutdown()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the standalone Windows proxy spike")
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="Loopback address (fixed to 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-dir", type=Path, help="Use the same data directory for CA commands")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("mitmproxy").setLevel(logging.WARNING)
    try:
        asyncio.run(serve(args.host, args.port, data_dir=args.data_dir))
    except KeyboardInterrupt:
        logging.getLogger("sentriflow.proxy.spike").info("Proxy stopped")
    except (OSError, ValueError) as error:
        print(f"Could not start the SentriFlow spike proxy: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
