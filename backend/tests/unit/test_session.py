import asyncio

import pytest

from sentriflow.cli import main, seed_demo
from sentriflow.config import Settings
from sentriflow.session import maintenance_session


def test_seed_and_reset_refuse_to_change_a_running_session(tmp_path):
    config = Settings(data_dir=tmp_path)
    config.database_path.write_bytes(b"existing-history")
    with maintenance_session(tmp_path):
        with pytest.raises(RuntimeError, match="Another SentriFlow"):
            asyncio.run(seed_demo(config))
        assert main(["reset", "--confirm", "--data-dir", str(tmp_path)]) == 1
        assert config.database_path.read_bytes() == b"existing-history"
        assert (tmp_path / "session.lock").exists()
    assert not (tmp_path / "session.lock").exists()


def test_confirmed_reset_after_stop_leaves_ca_files(tmp_path):
    config = Settings(data_dir=tmp_path)
    config.database_path.write_bytes(b"old-history")
    config.ca_dir.mkdir()
    certificate = config.ca_dir / "mitmproxy-ca-cert.pem"
    certificate.write_text("retained-public-certificate")
    assert main(["reset", "--confirm", "--data-dir", str(tmp_path)]) == 0
    assert not config.database_path.exists() and certificate.exists()
