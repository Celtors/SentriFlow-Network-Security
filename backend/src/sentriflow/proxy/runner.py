"""Standalone embedded mitmproxy runner for the Windows feasibility spike."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from sentriflow.proxy.addon import ConsoleFlowAddon

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


async def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the proxy in this process until interrupted."""
    if host != DEFAULT_HOST:
        raise ValueError("The spike proxy must bind to 127.0.0.1 only")
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")

    options = Options(listen_host=host, listen_port=port)
    master = DumpMaster(options, with_termlog=False, with_dumper=False)
    master.addons.add(ConsoleFlowAddon())
    logging.getLogger("sentriflow.proxy.spike").info(
        "Starting local proxy at http://%s:%d; CA files are in %s",
        host,
        port,
        options.confdir,
    )
    try:
        await master.run()
    finally:
        master.shutdown()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST, help="Loopback address (fixed to 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("mitmproxy").setLevel(logging.WARNING)
    try:
        asyncio.run(serve(args.host, args.port))
    except KeyboardInterrupt:
        logging.getLogger("sentriflow.proxy.spike").info("Proxy stopped")
    except (OSError, ValueError) as exc:
        print(f"Could not start the SentriFlow spike proxy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
