"""SentriFlow CLI: run | doctor | restore-proxy | install-ca | remove-ca | seed-demo | reset."""

import argparse

from sentriflow import __version__

COMMANDS = ["run", "doctor", "restore-proxy", "install-ca", "remove-ca", "seed-demo", "reset"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentriflow")
    parser.add_argument("command", choices=COMMANDS, nargs="?", default="run")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    print(f"sentriflow {__version__}: '{args.command}' not implemented yet")
    return 0
