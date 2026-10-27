import os
import sys
from pathlib import Path


def data_directory() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / "SentriFlow"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "sentriflow"
