"""Reproducible public-corpus training; never fetches websites in the corpus.

python -m sentriflow.ml.train --dataset .runtime/datasets/phiusiil.zip
Training requires backend[ml]. Inference deliberately uses a data-only JSON artifact.
"""

import argparse
import csv
import hashlib
import io
import json
import platform
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from sentriflow.ml.features import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    canonical_origin,
    extract_features,
    host_from_url,
    registered_domain,
)

DATA_SOURCE = "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset"
SEED = 42
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "models"


def prepare(dataset: Path):
    """Inspect columns/labels, remove invalid/exact duplicate and conflicting URLs."""
    archive_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
    unique = {}
    conflicts = set()
    invalid = duplicates = total = 0
    labels = Counter()
    with zipfile.ZipFile(dataset) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError("Expected exactly one CSV in official archive")
        with archive.open(names[0]) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
            columns = reader.fieldnames
            if not columns or not {"URL", "label"}.issubset(columns):
                raise ValueError("Dataset schema differs from inspected UCI schema")
            for row in reader:
                total += 1
                if row["label"] not in {"0", "1"}:
                    raise ValueError("Unexpected class label")
                labels[row["label"]] += 1
                label = 1 - int(row["label"])  # UCI 1=legitimate -> our 1=phishing.
                url = row["URL"].strip()
                host = host_from_url(url)
                features = extract_features(url)
                if host is None or features is None:
                    invalid += 1
                    continue
                key = canonical_origin(url)
                if key in unique:
                    duplicates += 1
                    if unique[key][1] != label:
                        conflicts.add(key)
                else:
                    unique[key] = (features, label, registered_domain(host))
    for key in conflicts:
        del unique[key]
    records = list(unique.values())
    x = np.asarray([r[0] for r in records], dtype=np.float64)
    y = np.asarray([r[1] for r in records], dtype=np.int8)
    groups = np.asarray([r[2] for r in records])
    metadata = {
        "source": DATA_SOURCE,
        "authors": ["Arvind Prasad", "Shalini Chandra"],
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "archive_sha256": archive_hash,
        "csv": names[0],
        "columns": columns,
        "original_labels": dict(labels),
        "positive_class": "1=phishing (inverted UCI label)",
        "source_rows": total,
        "invalid_rows": invalid,
        "duplicate_rows": duplicates,
        "conflicting_urls_removed": len(conflicts),
        "retained_rows": len(y),
        "registered_domain_groups": len(set(groups)),
        "training_inputs": (
            "Only recomputed numeric domain structure; no path/query or provided derived columns"
        ),
    }
    return x, y, groups, metadata


def split_groups(x, y, groups):
    def divide(indices, fraction, seed):
        a, b = next(
            GroupShuffleSplit(n_splits=1, test_size=fraction, random_state=seed).split(
                x[indices], y[indices], groups[indices]
            )
        )
        return indices[a], indices[b]

    rest, test = divide(np.arange(len(y)), 0.15, SEED)
    rest, calibration = divide(rest, 0.15 / 0.85, SEED + 1)
    train, selection = divide(rest, 0.10 / 0.70, SEED + 2)
    splits = {"train": train, "selection": selection, "calibration": calibration, "test": test}
    for name, indices in splits.items():
        if len(np.unique(y[indices])) != 2:
            raise ValueError(f"Missing class in {name}")
        for other, other_indices in splits.items():
            if name != other and set(groups[indices]) & set(groups[other_indices]):
                raise AssertionError("Registered-domain leakage")
    return splits


def metrics(y, probabilities):
    predicted = probabilities >= 0.5
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    bins = []
    for index in range(10):
        mask = (probabilities >= index / 10) & (
            probabilities <= 1 if index == 9 else probabilities < (index + 1) / 10
        )
        if mask.any():
            bins.append(
                {
                    "lower": index / 10,
                    "count": int(mask.sum()),
                    "mean_probability": float(probabilities[mask].mean()),
                    "phishing_frequency": float(y[mask].mean()),
                }
            )
    return {
        "accuracy": float(accuracy_score(y, predicted)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted)),
        "f1": float(f1_score(y, predicted)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "brier": float(brier_score_loss(y, probabilities)),
        "false_positive_rate": float(fp / (fp + tn)),
        "false_negative_rate": float(fn / (fn + tp)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "ece_10_bins": sum(
            b["count"] * abs(b["mean_probability"] - b["phishing_frequency"]) for b in bins
        )
        / len(y),
        "reliability_bins": bins,
    }


def export_estimator(estimator):
    if isinstance(estimator, RandomForestClassifier):
        trees = []
        for member in estimator.estimators_:
            tree = member.tree_
            values = tree.value[:, 0, :]
            trees.append(
                {
                    "left": tree.children_left.tolist(),
                    "right": tree.children_right.tolist(),
                    "feature": tree.feature.tolist(),
                    "threshold": tree.threshold.tolist(),
                    "positive": (values[:, 1] / values.sum(axis=1)).tolist(),
                }
            )
        return {"kind": "random_forest", "trees": trees}
    scaler, classifier = estimator.steps[0][1], estimator.steps[1][1]
    return {
        "kind": "logistic_regression",
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": classifier.coef_[0].tolist(),
        "intercept": float(classifier.intercept_[0]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    print("Inspecting corpus and extracting numeric structure...", flush=True)
    x, y, groups, metadata = prepare(args.dataset)
    splits = split_groups(x, y, groups)
    report = {
        "seed": SEED,
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": metadata,
        "feature_version": FEATURE_VERSION,
        "features": list(FEATURE_NAMES),
        "split_method": "Disjoint registered domains including private PSL; 60/10/15/15 groups",
        "splits": {
            name: {
                "rows": len(i),
                "groups": len(set(groups[i])),
                "phishing": int(y[i].sum()),
                "legitimate": int((y[i] == 0).sum()),
            }
            for name, i in splits.items()
        },
        "group_overlap": 0,
    }
    (args.output / "data_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"dataset": metadata, "splits": report["splits"]}), flush=True)
    if args.prepare_only:
        return
    train, selection, calibration, test = (
        splits[k] for k in ("train", "selection", "calibration", "test")
    )
    candidates = {
        "random_forest": RandomForestClassifier(
            n_estimators=96, max_depth=12, min_samples_leaf=8, n_jobs=4, random_state=SEED
        ),
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1500, random_state=SEED)
        ),
    }
    comparisons = {}
    for name, estimator in candidates.items():
        print(f"Fitting {name}...", flush=True)
        estimator.fit(x[train], y[train])
        comparisons[name] = metrics(y[selection], estimator.predict_proba(x[selection])[:, 1])
    selected = max(comparisons, key=lambda name: comparisons[name]["roc_auc"])
    estimator = candidates[selected]
    # Selection, calibrator and final test never participate in base-estimator fitting.
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(estimator.predict_proba(x[calibration])[:, 1], y[calibration])
    raw = estimator.predict_proba(x[test])[:, 1]
    calibrated = calibrator.predict(raw)
    report["global_feature_importance"] = (
        dict(zip(FEATURE_NAMES, estimator.feature_importances_.tolist(), strict=True))
        if selected == "random_forest"
        else None
    )
    report["feature_summary_by_class"] = {
        str(label): {
            name: {
                "mean": float(x[y == label, i].mean()),
                "median": float(np.median(x[y == label, i])),
            }
            for i, name in enumerate(FEATURE_NAMES)
        }
        for label in (0, 1)
    }
    report.update(
        selected=selected,
        selection_comparison=comparisons,
        selection_criterion="Highest selection ROC AUC; test untouched until selection frozen",
        calibration="Isotonic regression fitted only on disjoint calibration domains",
        test_uncalibrated=metrics(y[test], raw),
        test_calibrated=metrics(y[test], calibrated),
        test_prior_baseline=metrics(y[test], np.full(len(test), y[train].mean())),
        thresholds={
            "low_below": 0.30,
            "high_at_or_above": 0.70,
            "classification": 0.50,
            "policy": "Fixed display thresholds, not optimized on test",
        },
    )
    artifact = {
        "schema": 1,
        "model_id": f"phiusiil-domain-v2-{metadata['archive_sha256'][:12]}",
        "feature_version": FEATURE_VERSION,
        "features": list(FEATURE_NAMES),
        "positive_class": "phishing",
        "scope": "Domain-structure phishing classification",
        "estimator": export_estimator(estimator),
        "calibration": {
            "method": "isotonic",
            "x": calibrator.X_thresholds_.tolist(),
            "y": calibrator.y_thresholds_.tolist(),
        },
        "reference": np.median(x[train], axis=0).tolist(),
        "thresholds": report["thresholds"],
        "dataset": metadata,
        "metrics": report["test_calibrated"],
    }
    artifact_path = args.output / "website-risk.json"
    artifact_path.write_text(
        json.dumps(artifact, separators=(",", ":"), allow_nan=False), encoding="utf-8"
    )
    # Validate portable runtime against sklearn, including its float32 tree input convention.
    from sentriflow.ml.predictor import Predictor

    runtime = Predictor(artifact_path, verify=False)
    exported = np.array([runtime.probability(row.tolist()) for row in x[test]])
    error = float(np.max(np.abs(exported - calibrated)))
    report["export_max_absolute_error"] = error
    if error > 1e-7:
        raise AssertionError(f"Export parity failed: {error}")
    report["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    report["artifact_bytes"] = artifact_path.stat().st_size
    (args.output / "training_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (args.output / "website-risk.sha256").write_text(
        report["artifact_sha256"] + "\n", encoding="ascii"
    )
    print(
        json.dumps(
            {
                "selected": selected,
                "test": report["test_calibrated"],
                "export_error": error,
                "artifact_bytes": report["artifact_bytes"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
