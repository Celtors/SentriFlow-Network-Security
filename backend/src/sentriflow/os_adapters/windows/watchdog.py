"""Compatibility entry point for the shared Windows proxy recovery watchdog."""

import argparse
from pathlib import Path

from sentriflow.os_adapters.windows.system_proxy import watch as watch

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", type=int, required=True)
    parser.add_argument("--started", type=float, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    watch(args.watch, args.started, args.state)
