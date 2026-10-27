import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from sentriflow import __version__
from sentriflow.config import Settings

COMMANDS = ["run", "doctor", "restore-proxy", "install-ca", "remove-ca", "seed-demo", "reset"]


async def seed_demo(config: Settings) -> None:
    from sentriflow.application import Runtime
    from sentriflow.core.models import CustomPattern

    runtime = Runtime(config)
    await runtime.open()
    try:
        await runtime.patterns.save(
            CustomPattern(id="demo-name", label="Demo name", pattern="Alex Example")
        )
        await runtime.patterns.save(
            CustomPattern(id="demo-canary", label="project_canary", pattern="dummy-project-canary")
        )
        await runtime.blocklist.add("tracker.demo.test", "demo (synthetic)")
    finally:
        await runtime.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentriflow")
    parser.add_argument("command", choices=COMMANDS, nargs="?", default="run")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--api-port", type=int)
    parser.add_argument("--proxy-port", type=int)
    parser.add_argument("--import-blocklist", type=Path)
    parser.add_argument("--system-proxy", action="store_true", help="Opt in to Windows routing")
    parser.add_argument("--api-only", action="store_true", help="Run REST/WS without interception")
    parser.add_argument("--consent", action="store_true", help="Consent to current-user CA trust")
    parser.add_argument("--confirm", action="store_true", help="Confirm history deletion")
    args = parser.parse_args(argv)
    config = Settings(
        **{
            name: getattr(args, name)
            for name in ("data_dir", "api_port", "proxy_port")
            if getattr(args, name) is not None
        }
    )
    try:
        if args.command == "run":
            from sentriflow.proxy.runner import run

            if args.import_blocklist:
                from sentriflow.application import Runtime
                from sentriflow.intel.blocklist_loader import parse_domains

                async def import_domains() -> None:
                    rt = Runtime(config)
                    await rt.open()
                    try:
                        domains, skipped = parse_domains(
                            args.import_blocklist.read_text(encoding="utf-8")
                        )
                        count = await rt.blocklist.replace_source(
                            args.import_blocklist.name, domains
                        )
                        print(f"Imported {count} domains; skipped {skipped} unsupported entries.")
                    finally:
                        await rt.close()

                asyncio.run(import_domains())
            asyncio.run(run(config, system_proxy=args.system_proxy, api_only=args.api_only))
        elif args.command == "seed-demo":
            asyncio.run(seed_demo(config))
            print("Seeded dummy name and synthetic tracker; no external lists downloaded.")
        elif args.command == "doctor":
            from sentriflow.os_adapters.windows.cert_store import ca_status

            print(
                json.dumps(
                    {
                        "version": __version__,
                        "platform": sys.platform,
                        "data_dir": str(config.data_dir),
                        "proxy_recovery_needed": (config.data_dir / "state.json").exists(),
                        "ca": ca_status(config.ca_dir),
                    },
                    indent=2,
                )
            )
        elif args.command == "restore-proxy":
            from sentriflow.os_adapters.windows.system_proxy import SystemProxy

            restored = SystemProxy(config.data_dir / "state.json").restore()
            print("Proxy restored." if restored else "No saved proxy state.")
        elif args.command in ("install-ca", "remove-ca"):
            from sentriflow.os_adapters.windows.cert_store import install_ca, remove_ca

            result = (
                install_ca(config.ca_dir, confirmed=args.consent or args.confirm)
                if args.command == "install-ca"
                else remove_ca(config.ca_dir)
            )
            print(json.dumps(result, indent=2))
        elif args.command == "reset":
            if not args.confirm:
                parser.error("reset requires --confirm (stop SentriFlow first)")
            if (config.data_dir / "state.json").exists():
                raise ValueError("Restore the system proxy before resetting")
            for suffix in ("", "-wal", "-shm"):
                Path(str(config.database_path) + suffix).unlink(missing_ok=True)
            print(
                "Local database cleared. CA files and trust are retained; use remove-ca to untrust."
            )
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"SentriFlow: {error}", file=sys.stderr)
        return 1
