"""Restore a dead session's proxy journal. Launched only after an explicit proxy-enable command."""

import json
import sys
import time
from pathlib import Path

from sentriflow.os_adapters.windows.system_proxy import WindowsProxy


def watch(adapter: WindowsProxy, pid: int, created: float, interval: float = 0.5) -> int:
    while adapter.journal.exists():
        try:
            journal = json.loads(adapter.journal.read_text(encoding="utf-8"))
            if journal.get("pid") != pid or journal.get("created") != created:
                return 0
            if not adapter.owner_alive(journal):
                adapter.restore()
                return 0
        except (ValueError, OSError, RuntimeError):
            # Keep the recovery journal if an external change requires manual attention.
            return 1
        time.sleep(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(
        watch(
            WindowsProxy(Path(sys.argv[1]), int(sys.argv[2])), int(sys.argv[3]), float(sys.argv[4])
        )
    )
