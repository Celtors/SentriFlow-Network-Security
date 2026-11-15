"""Validated data-only estimator, with no pickle loading or inference network calls."""

import bisect
import hashlib
import json
import math
import struct
from pathlib import Path

from sentriflow.ml.features import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    extract_features,
    host_from_url,
    is_public_host,
)

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "models" / "website-risk.json"
LABELS = {
    "url_length": "Address length",
    "host_length": "Domain length",
    "path_length": "Page path length",
    "query_length": "Query length",
    "https_scheme": "HTTPS in the observed address",
    "host_is_ip": "IP address as domain",
    "subdomain_count": "Number of subdomains",
    "longest_label": "Longest domain segment",
    "tld_length": "Domain suffix length",
    "host_digits": "Digits in domain",
    "host_digit_ratio": "Proportion of digits in domain",
    "host_hyphens": "Hyphens in domain",
    "host_entropy": "Domain character variation",
    "punycode": "Internationalized domain encoding",
    "path_depth": "Page path depth",
    "url_dots": "Dots in address",
    "url_hyphens": "Hyphens in address",
    "url_at": "At signs in address",
    "url_percent": "Percent encodings",
    "url_equals": "Equals signs in address",
    "url_ampersands": "Parameter separators",
    "url_digits": "Digits in address",
    "query_parameters": "Number of query parameters",
    "nonstandard_port": "Nonstandard port",
}


class Predictor:
    def __init__(self, path: Path = MODEL_PATH, *, verify: bool = True):
        raw = path.read_bytes()
        if len(raw) > 30_000_000:
            raise ValueError("Model artifact exceeds size limit")
        if verify:
            expected = path.with_suffix(".sha256").read_text(encoding="ascii").strip()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("Model checksum mismatch")
        data = json.loads(raw)
        if (
            data["schema"] != 1
            or data["feature_version"] != FEATURE_VERSION
            or data["features"] != list(FEATURE_NAMES)
            or data["positive_class"] != "phishing"
        ):
            raise ValueError("Unsupported model/feature/class schema")
        self.data = data
        self.estimator = data["estimator"]
        self.reference = data["reference"]
        self.knots, self.values = data["calibration"]["x"], data["calibration"]["y"]
        if (
            data["calibration"]["method"] != "isotonic"
            or len(self.knots) < 2
            or len(self.knots) != len(self.values)
            or not all(math.isfinite(v) for v in self.knots + self.values + self.reference)
            or any(a >= b for a, b in zip(self.knots, self.knots[1:], strict=False))
            or any(a > b for a, b in zip(self.values, self.values[1:], strict=False))
            or any(v < 0 or v > 1 for v in self.values)
            or len(self.reference) != len(FEATURE_NAMES)
        ):
            raise ValueError("Invalid calibration/reference")
        if self.estimator["kind"] == "random_forest":
            trees = self.estimator["trees"]
            if not trees or len(trees) > 512:
                raise ValueError("Invalid forest")
            for tree in trees:
                size = len(tree["left"])
                if (
                    size == 0
                    or size > 100_000
                    or any(
                        len(tree[k]) != size for k in ("right", "feature", "threshold", "positive")
                    )
                ):
                    raise ValueError("Invalid tree shape")
                for i, child in enumerate(tree["left"]):
                    if child != -1 and not (
                        i < child < size
                        and i < tree["right"][i] < size
                        and 0 <= tree["feature"][i] < len(FEATURE_NAMES)
                    ):
                        raise ValueError("Invalid tree child")
                    if not (0 <= tree["positive"][i] <= 1 and math.isfinite(tree["threshold"][i])):
                        raise ValueError("Invalid tree value")
        elif self.estimator["kind"] == "logistic_regression":
            for key in ("mean", "scale", "coef"):
                if len(self.estimator[key]) != len(FEATURE_NAMES):
                    raise ValueError("Invalid logistic coefficients")
        else:
            raise ValueError("Unsupported estimator")
        # Fail at loading rather than emitting a fake score on the first request.
        self.probability(self.reference)

    def probability(self, features: list[float]) -> float:
        if len(features) != len(FEATURE_NAMES) or not all(math.isfinite(v) for v in features):
            raise ValueError("Unavailable or invalid numeric features")
        if self.estimator["kind"] == "random_forest":
            # sklearn trees cast their input to float32. Match that boundary exactly.
            vector = struct.unpack(f"{len(features)}f", struct.pack(f"{len(features)}f", *features))
            total = 0.0
            for tree in self.estimator["trees"]:
                node = 0
                while tree["left"][node] != -1:
                    node = (
                        tree["left"][node]
                        if vector[tree["feature"][node]] <= tree["threshold"][node]
                        else tree["right"][node]
                    )
                total += tree["positive"][node]
            raw = total / len(self.estimator["trees"])
        else:
            est = self.estimator
            z = est["intercept"] + sum(
                (v - m) / s * c
                for v, m, s, c in zip(features, est["mean"], est["scale"], est["coef"], strict=True)
            )
            raw = 1 / (1 + math.exp(-max(-700, min(700, z))))
        position = bisect.bisect_right(self.knots, raw)
        if position == 0:
            return float(self.values[0])
        if position >= len(self.knots):
            return float(self.values[-1])
        a, b = position - 1, position
        fraction = (raw - self.knots[a]) / (self.knots[b] - self.knots[a])
        return float(self.values[a] + fraction * (self.values[b] - self.values[a]))

    def analyze(self, url: str) -> dict:
        host = host_from_url(url)
        features = extract_features(url)
        if host is None or features is None or not is_public_host(host):
            return {
                "state": "unavailable",
                "reason": "A public HTTP(S) address is required; "
                "local, malformed or overlong addresses are outside training scope.",
                "maliciousness_percentage": None,
                "risk_level": "unknown",
                "reasons": [],
            }
        probability = self.probability(features)
        contributions = []
        for i, name in enumerate(FEATURE_NAMES):
            changed = features.copy()
            changed[i] = self.reference[i]
            delta = probability - self.probability(changed)
            if abs(delta) >= 0.001:
                contributions.append(
                    {
                        "feature": name,
                        "label": LABELS[name],
                        "value": features[i],
                        "delta_percentage_points": round(delta * 100, 2),
                    }
                )
        contributions.sort(key=lambda c: abs(c["delta_percentage_points"]), reverse=True)
        top = contributions[:3]
        reasons = [
            f"{c['label']} {'raises' if c['delta_percentage_points'] > 0 else 'lowers'} "
            "the model estimate."
            for c in top
        ]
        if not reasons:
            reasons = ["The address structure is close to the model's reference examples."]
        low = self.data["thresholds"]["low_below"]
        high = self.data["thresholds"]["high_at_or_above"]
        return {
            "state": "ready",
            "model_id": self.data["model_id"],
            "maliciousness_percentage": round(probability * 100, 1),
            "risk_level": "high"
            if probability >= high
            else "low"
            if probability < low
            else "medium",
            "verdict": "likely_phishing" if probability >= 0.5 else "lower_phishing_risk",
            "reasons": reasons,
            "contributions": top,
            "features": dict(zip(FEATURE_NAMES, features, strict=True)),
            "scope": self.data["scope"],
            "calibration": "isotonic",
            "explanation_method": "One feature at a time replaced with training median; "
            "local sensitivity, not causal proof or additive contributions.",
            "caution": "Calibrated on a reference phishing corpus, not a guarantee of safety. "
            "It cannot establish malware, reputation or actual browser behavior.",
        }

    def status(self) -> dict:
        return {
            "available": True,
            "model_id": self.data["model_id"],
            "algorithm": self.estimator["kind"],
            "scope": self.data["scope"],
            "calibration": "isotonic",
            "features": list(FEATURE_NAMES),
            "metrics": self.data["metrics"],
            "dataset": {key: self.data["dataset"][key] for key in ("source", "license", "authors")},
        }
