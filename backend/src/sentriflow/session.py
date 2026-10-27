"""One live owner per local data directory, shared by launch and maintenance commands."""

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psutil


def acquire_session(data_dir: Path) -> Path:
    lock = data_dir / "session.lock"
    if lock.exists():
        previous = json.loads(lock.read_text(encoding="utf-8"))
        try:
            process = psutil.Process(previous["pid"])
            if abs(process.create_time() - previous["created"]) < 0.01:
                raise RuntimeError("Another SentriFlow instance is using this data directory")
        except psutil.Error:
            pass
        lock.unlink()
    with lock.open("x", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "created": psutil.Process().create_time()}, stream)
    return lock


@contextmanager
def maintenance_session(data_dir: Path) -> Iterator[None]:
    from sentriflow.os_adapters.windows.file_acl import restrict_private_directory

    restrict_private_directory(data_dir)
    lock = acquire_session(data_dir)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)
