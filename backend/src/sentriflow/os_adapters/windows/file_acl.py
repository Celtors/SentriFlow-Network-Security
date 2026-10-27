import csv
import os
import subprocess
from pathlib import Path


def restrict_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        output = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=True
        ).stdout
        sid = next(csv.reader([output.strip()]))[1]
        subprocess.run(
            [
                "icacls",
                str(path.resolve()),
                "/inheritance:r",
                "/grant:r",
                f"*{sid}:(OI)(CI)F",
                "*S-1-5-18:(OI)(CI)F",
            ],
            capture_output=True,
            check=True,
        )
    else:
        path.chmod(0o700)
