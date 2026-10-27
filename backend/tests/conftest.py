import pytest

from sentriflow.config import Config
from sentriflow.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    app = Runtime(Config(data_dir=tmp_path))
    yield app
    app.halts.shutdown()
    app.geoip.close()
    app.db.close()
