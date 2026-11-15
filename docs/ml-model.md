# Website risk model

The shipped model is an actual Random Forest trained on public labeled URLs, with
isotonic probability calibration on separate domains. It estimates **phishing
likelihood from domain structure**, not every kind of maliciousness. It does not
decide whether to block a request; existing privacy controls remain independent.

## Data and attribution

Arvind Prasad and Shalini Chandra (2024), **PhiUSIIL Phishing URL (Website)**,
[UCI dataset 967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset).
Dataset license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
This work adapts the source by deduplicating origins, inverting labels and
extracting new numeric features; it is not endorsed by the original authors.

Official archive:
`https://archive.ics.uci.edu/static/public/967/phiusiil%2Bphishing%2Burl%2Bdataset.zip`

SHA256: `0a639fd03aea6308c5b1c10c92aa23c2ce1505447a9137271865cd0badc9a59a`.
235,795 source rows, 56 actual columns including URL and label. UCI's **1 means
legitimate**, so training explicitly transforms `y = 1 - source_label`. Runtime
positive-class output is always phishing. None of the source's precomputed HTML,
title, similarity or reputation columns is used.

Paths, queries, fragments, userinfo and conventional `www.` prefixes are discarded
before feature extraction. This avoids learning systematic differences in URL
formatting between the collected classes and prevents sensitive page/query values
from entering the estimator. Origin duplicates are removed and all origins with
conflicting labels discarded: 14,414 repeated rows, 12 conflicting origins,
221,369 retained origins in 197,699 registered-domain groups.

No URL in the dataset is visited. The archive remains under ignored `.runtime/`;
only the derived model, numeric aggregate reports and attribution ship in Git.

## Inputs and matching live inference

`backend/src/sentriflow/ml/features.py` is shared without a separate runtime
implementation. Feature schema **2** has 13 values, in this order:

| Feature | Definition |
| --- | --- |
| host_length | ASCII/IDNA hostname characters after removing leading `www.` |
| https_scheme | Observed HTTPS scheme; not a certificate/reputation/trust claim |
| host_is_ip | Whether hostname parses as an IPv4/IPv6 literal |
| subdomain_count | Labels above the registered domain, using offline private-aware PSL |
| longest_label | Longest dot-separated hostname segment |
| tld_length | Characters in the public suffix |
| host_digits | Digit characters in normalized hostname |
| host_digit_ratio | Digits divided by hostname length |
| host_hyphens | Hyphen characters in hostname |
| host_entropy | Shannon entropy of hostname characters, in bits |
| punycode | Presence of an `xn--` domain label |
| host_dots | Dot characters in hostname |
| nonstandard_port | Explicit port differs from HTTP 80 / HTTPS 443 |

Malformed/overlong URLs and local/private/reserved hosts yield no estimate. Missing
payload/browser behavior does not become a fake zero feature: it is outside this
model's inputs. Domain age, blacklist membership, cookies, actual tokens/passwords,
form values, permissions and fingerprinting are never model inputs. The model
cannot detect a compromised page purely from a legitimate domain's name.

## Training and evaluation

Seed 42. GroupShuffleSplit by registered domains including private suffixes such
as `github.io`; no domain group overlaps any split. Requested group allocation is
60% fit, 10% model selection, 15% calibration, 15% final test. Actual row counts:

| Split | Rows | Legitimate | Phishing |
| --- | ---: | ---: | ---: |
| Fit | 135,209 | 81,025 | 54,184 |
| Selection | 21,561 | 13,483 | 8,078 |
| Calibration | 32,310 | 20,183 | 12,127 |
| Test | 32,289 | 20,147 | 12,142 |

Random Forest: 96 trees, depth <=12, minimum 8 samples per leaf. Compared against
scaled Logistic Regression; selection ROC AUC **0.96961 vs 0.96482**, respectively.
The winner is selected before the final model's test evaluation. The base model
uses only fit rows; isotonic calibration uses only calibration rows. See official
[calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).

Final calibrated test results at probability >=0.5:

| Metric | Value |
| --- | ---: |
| Accuracy | 95.996% |
| Phishing precision | 98.342% |
| Phishing recall | 90.883% |
| F1 | 94.466% |
| ROC AUC | 0.97003 |
| False-positive rate | 0.923% (186 / 20,147 legitimate) |
| False-negative rate | 9.117% (1,107 / 12,142 phishing) |
| Brier, before / after calibration | 0.036154 / 0.035100 |
| Expected calibration error, 10 bins | 0.002652 |

TN=19,961, FP=186, FN=1,107, TP=11,035. Reliability-bin counts/frequencies,
baseline metrics, candidate metrics, class feature summaries and global forest
importances are in `backend/src/sentriflow/data/models/training_report.json`.
The HTTPS feature has substantial source-corpus importance (~46%); a phishing
site can use HTTPS and a legitimate HTTP site can be overestimated.

These are **internal corpus results**, not a deployment accuracy promise. The
initial engineering model was rejected on ordinary-address smoke probes because
of path-format artifacts; schema 2 removes that information entirely. This is an
iterative engineering evaluation, not a preregistered experiment or an independent
temporal test. There is no recent production ground truth, external-corpus test,
or deployment-prior correction. Similar collection sources and temporal/domain
shift can invalidate calibration. Rare middle-probability bins have few examples.

## Artifact and probability semantics

`backend/src/sentriflow/data/models/website-risk.json` is a 2.1 MB data-only export
of the learned tree arrays, positive-class leaf frequencies, training medians and
isotonic knots. `website-risk.sha256` verifies integrity; no pickle/joblib code is
loaded. The shipped artifact runs without sklearn/numpy and needs no training or
network access after installation. Python/scikit-learn versions are in the report.

The raw value is the mean tree phishing probability, transformed using the learned
monotone isotonic calibration curve. The reported percentage is 100 times that
value, rounded to one decimal place. Calibration corresponds to this reference
corpus; it is not the probability of all internet harm. UI renders endpoints as
`<0.1%` / `>99.9%` to avoid suggesting certainty. Fixed display tiers are low <30%,
medium 30% to <70%, high >=70%; these are display policy, not tuned test thresholds.

Each explanation replaces one numeric feature with its fit-set median and runs
the model again. The largest local probability changes are shown with direction.
These sensitivity results are not causal or additive contributions. Browser
behavior is displayed separately and never invented to explain the model.

Portable inference was compared with sklearn on **every held-out test row**:
maximum absolute difference `3.062e-14`. Export matches sklearn's float32 input
conversion and positive-class ordering. Missing/corrupt artifacts report unavailable
and leave existing traffic enforcement operational.

## Reproduce

From repository root (Python 3.12+, tested here with Python 3.13):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[dev,browser,ml]"
New-Item -ItemType Directory -Force .runtime/datasets | Out-Null
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri 'https://archive.ics.uci.edu/static/public/967/phiusiil%2Bphishing%2Burl%2Bdataset.zip' -OutFile .runtime/datasets/phiusiil-verified.zip
.\.venv\Scripts\python.exe -m sentriflow.ml.train --dataset .runtime/datasets/phiusiil-verified.zip
```

`--prepare-only` inspects/prepares without fitting. For experimental retraining use
`--output .runtime/experimental-model` so the shipped artifact is not overwritten
until its report and inference parity are reviewed. Never add the raw archive or
private browsing history to Git. Dataset version/hash and all split counts must
be checked when reproducing. Training is intentionally explicit, never automatic
at application startup.
