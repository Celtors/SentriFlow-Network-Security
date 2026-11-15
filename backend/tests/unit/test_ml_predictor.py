import hashlib
import json

import pytest

from sentriflow.ml.features import FEATURE_NAMES, FEATURE_VERSION
from sentriflow.ml.predictor import Predictor


def artifact(tmp_path):
    """Tiny test estimator verifies traversal/class/calibration, never ships to the app."""
    data = {
        "schema": 1,
        "feature_version": FEATURE_VERSION,
        "features": list(FEATURE_NAMES),
        "positive_class": "phishing",
        "reference": [0.0] * len(FEATURE_NAMES),
        "estimator": {
            "kind": "random_forest",
            "trees": [
                {
                    "left": [1, -1, -1],
                    "right": [2, -1, -1],
                    "feature": [0, -2, -2],
                    "threshold": [30.0, -2.0, -2.0],
                    "positive": [0.5, 0.1, 0.9],
                }
            ],
        },
        "calibration": {"method": "isotonic", "x": [0.0, 1.0], "y": [0.0, 1.0]},
    }
    path = tmp_path / "test.json"
    path.write_text(json.dumps(data))
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest())
    return path


def test_correct_positive_class_and_tree_traversal(tmp_path):
    model = Predictor(artifact(tmp_path))
    assert model.probability([20.0] + [0.0] * (len(FEATURE_NAMES) - 1)) == 0.1
    assert model.probability([40.0] + [0.0] * (len(FEATURE_NAMES) - 1)) == 0.9
    for invalid in ([], [float("nan")] * len(FEATURE_NAMES)):
        with pytest.raises(ValueError):
            model.probability(invalid)
    assert model.analyze("http://localhost/private")["state"] == "unavailable"


def test_corrupt_artifact_is_rejected(tmp_path):
    path = artifact(tmp_path)
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="checksum"):
        Predictor(path)


def test_cyclic_tree_is_rejected_even_without_checksum(tmp_path):
    path = artifact(tmp_path)
    data = json.loads(path.read_text())
    data["estimator"]["trees"][0]["left"][0] = 0
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="child"):
        Predictor(path, verify=False)
