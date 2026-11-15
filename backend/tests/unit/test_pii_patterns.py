import gzip

import pytest

from sentriflow.core.models import CustomPattern
from sentriflow.inspection.pipeline import analyze
from sentriflow.inspection.tracker_matcher import TrackerMatcher


@pytest.mark.parametrize(
    "body,headers",
    [
        (
            b'{"name":"Alex Example","email":"alex@example.test","card":"4111111111111111"}',
            {"content-type": "application/json"},
        ),
        (
            b"name=Alex+Example&email=alex%40example.test&card=4111111111111111",
            {"content-type": "application/x-www-form-urlencoded"},
        ),
        (
            b'--test\r\nContent-Disposition: form-data; name="name"\r\n\r\nAlex Example\r\n'
            b'--test\r\nContent-Disposition: form-data; name="email"\r\n\r\nalex@example.test\r\n'
            b'--test\r\nContent-Disposition: form-data; name="card"\r\n\r\n'
            b"4111111111111111\r\n--test--",
            {"content-type": "multipart/form-data; boundary=test"},
        ),
    ],
)
@pytest.mark.parametrize("compressed", [False, True])
def test_seeded_pii_across_encodings(body, headers, compressed):
    if compressed:
        body = gzip.compress(body)
        headers = {**headers, "content-encoding": "gzip"}
    findings = analyze(
        "demo.test",
        "http://demo.test/",
        headers,
        body,
        patterns=[CustomPattern(label="Demo name", pattern="Alex Example")],
        trackers=TrackerMatcher(),
    )
    assert {f.label for f in findings} >= {"Demo name", "Email address", "Payment card (Luhn)"}
    assert all(f.masked_sample == "[redacted]" for f in findings)


def test_encoded_json_url_and_headers():
    findings = analyze(
        "demo.test",
        "http://demo.test/?email=alex%40example.test",
        {"x-demo": "alex@example.test", "content-type": "application/json"},
        b'{"email":"alex\\u0040example.test"}',
        patterns=[],
        trackers=TrackerMatcher(),
    )
    assert {f.location for f in findings if f.label == "Email address"} == {
        "url",
        "headers",
        "body",
    }


@pytest.mark.parametrize(
    "body,headers",
    [
        (b"a" * 1_048_577, {}),
        (gzip.compress(b"a" * 2_000_000), {"content-encoding": "gzip"}),
        (b"broken gzip", {"content-encoding": "gzip"}),
        (b"abc", {"content-encoding": "br"}),
        (b"\xff", {"content-type": "application/json"}),
        (b'{"broken":', {"content-type": "application/json"}),
    ],
)
def test_uninspectable_body_has_explicit_finding(body, headers):
    findings = analyze(
        "demo.test", "http://demo.test", headers, body, patterns=[], trackers=TrackerMatcher()
    )
    assert any(f.type == "inspection_limit" for f in findings)


@pytest.mark.parametrize(
    "body,headers",
    [
        (b"\x00\xffstudent@example.test", {"content-type": "application/octet-stream"}),
        (b"\xff", {"content-type": "application/x-protobuf"}),
        (b"\xff", {"content-type": "image/png"}),
        (b"\xff", {"content-type": "audio/webm"}),
        (b"\xff", {"content-type": "application/octet-stream; name=form.json"}),
        (b"\xff", {}),
        (b"--test\r\n\xff\r\n--test--", {"content-type": "multipart/form-data; boundary=test"}),
        (
            b"not decoded",
            {"content-type": "application/octet-stream", "content-encoding": "br"},
        ),
        (b"a" * 1_048_577, {"content-type": "application/octet-stream"}),
    ],
)
def test_binary_body_excluded_but_url_and_headers_checked(body, headers):
    findings = analyze(
        "demo.test",
        "http://demo.test/?email=student%40example.test",
        {**headers, "x-demo-secret": "DEMO_SECRET"},
        body,
        patterns=[CustomPattern(label="Demo secret", pattern="DEMO_SECRET")],
        trackers=TrackerMatcher(),
    )
    assert any(f.type == "inspection_skipped" for f in findings)
    assert not any(f.type == "inspection_limit" for f in findings)
    assert {(f.label, f.location) for f in findings if f.type in {"pii", "custom"}} == {
        ("Email address", "url"),
        ("Demo secret", "headers"),
    }


def test_inspector_toggle_preserves_tracker_check():
    findings = analyze(
        "tracker.demo.test",
        "http://tracker.demo.test",
        {},
        b"alex@example.test",
        patterns=[],
        trackers=TrackerMatcher(["tracker.demo.test"]),
        enabled=False,
    )
    assert [f.type for f in findings] == ["tracker"]
