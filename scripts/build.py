"""Build and package the dashboard into the existing Python backend, on Windows or Linux."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Package an already validated frontend/dist",
    )
    args = parser.parse_args()
    if not args.skip_build:
        subprocess.run(
            ["npm.cmd" if os.name == "nt" else "npm", "run", "build"],
            cwd=ROOT / "frontend",
            check=True,
        )
    source = ROOT / "frontend" / "dist"
    if not (source / "index.html").is_file():
        raise SystemExit(
            "Frontend build is missing; run npm ci in frontend, then this command."
        )
    target = ROOT / "backend" / "src" / "sentriflow" / "web"
    expected = (ROOT / "backend" / "src" / "sentriflow").resolve() / "web"
    if (
        target.is_symlink()
        or target.resolve() != expected
        or not target.resolve().is_relative_to(ROOT.resolve())
    ):
        raise SystemExit(
            "Refusing to replace a dashboard directory outside this checkout"
        )
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    print("Dashboard packaged. Start with python -I -m sentriflow run.")


if __name__ == "__main__":
    main()
