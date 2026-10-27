"""SentriFlow CLI: run | doctor | restore-proxy | install-ca | remove-ca | seed-demo | reset."""

import argparse
import asyncio
import json
from pathlib import Path

from sentriflow import __version__
from sentriflow.config import Config
from sentriflow.launcher import run
from sentriflow.os_adapters.windows.cert_store import certificate_status, manage_ca
from sentriflow.os_adapters.windows.system_proxy import WindowsProxy

COMMANDS = ["run", "doctor", "restore-proxy", "install-ca", "remove-ca", "seed-demo", "reset"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentriflow")
    parser.add_argument("command", choices=COMMANDS, nargs="?", default="run")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--data-dir", type=Path, help="Override the private local data directory")
    parser.add_argument("--api-port", type=int)
    parser.add_argument("--proxy-port", type=int)
    parser.add_argument("--api-only", action="store_true")
    parser.add_argument("--import-blocklist", type=Path)
    parser.add_argument(
        "--confirm", action="store_true", help="Consent to CA trust or database reset"
    )
    args = parser.parse_args(argv)
    overrides = {
        name: getattr(args, name)
        for name in ("data_dir", "api_port", "proxy_port")
        if getattr(args, name) is not None
    }
    config = Config(**overrides, api_only=args.api_only)
    if config.api_port == config.proxy_port:
        parser.error("API and proxy must use different ports")
    try:
        if args.command == "run":
            asyncio.run(run(config, args.import_blocklist))
        elif args.command == "doctor":
            print(
                json.dumps(
                    {
                        "version": __version__,
                        "data_dir": str(config.data_dir),
                        "proxy": WindowsProxy(config.data_dir, config.proxy_port).status(),
                        "ca": certificate_status(config.data_dir / "ca"),
                        "routing": "Only explicitly routed HTTP(S) traffic is captured",
                    },
                    indent=2,
                )
            )
        elif args.command == "restore-proxy":
            print("Restored:", WindowsProxy(config.data_dir, config.proxy_port).restore())
        elif args.command in ("install-ca", "remove-ca"):
            if args.command == "install-ca" and not args.confirm:
                parser.error("install-ca requires --confirm to trust the local HTTPS certificate")
            manage_ca(config.data_dir / "ca", args.command == "install-ca")
            print("Local CA trust operation completed.")
        elif args.command == "seed-demo":
            print("Run: python demo/test-server/server.py")
            print("Dummy form: http://127.0.0.1:9090; see demo/demo-script.md")
        elif args.command == "reset":
            parser.error(
                "Automatic deletion is not supported. Back up local data and remove it manually."
            )
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"SentriFlow could not complete the operation: {type(exc).__name__}: {exc}")
        return 1
    return 0
