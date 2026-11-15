# Trained website-risk artifact

Derived by SentriFlow from **PhiUSIIL Phishing URL (Website)**, Arvind Prasad and
Shalini Chandra (2024), UCI Machine Learning Repository dataset 967:
https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset

Source data license: **Creative Commons Attribution 4.0 International**
(https://creativecommons.org/licenses/by/4.0/). No endorsement is implied.
Modifications: origin normalization, duplicate/conflict removal, numeric domain
feature extraction, disjoint-domain training/evaluation and isotonic calibration.
No raw dataset URL rows or private browsing values are distributed here.

`training_report.json` records the exact source hash, features, environment,
selection criteria, metrics and calibration bins. `website-risk.json` contains
learned numeric trees/calibration only, verified using `website-risk.sha256`.
See repository `docs/ml-model.md` for full usage, reproducibility and limitations.
