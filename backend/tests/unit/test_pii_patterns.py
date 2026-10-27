import gzip
import json
import time

import pytest

from sentriflow.inspection.payload_extractor import decode_body
from sentriflow.inspection.pipeline import analyze

DUMMY = {"email": "student@example.test", "phone": "+6281234567890", "card": "4111111111111111"}


@pytest.mark.parametrize("kind", ["json", "form", "gzip", "multipart"])
def test_seeded_pii_representations(kind):
    encoding = ""
    if kind in ("json", "gzip"):
        body = json.dumps(DUMMY).encode()
        content_type = "application/json"
        if kind == "gzip":
            encoding, body = "gzip", gzip.compress(body)
    elif kind == "form":
        body = b"email=student%40example.test&phone=%2B6281234567890&card=4111111111111111"
        content_type = "application/x-www-form-urlencoded"
    else:
        body = (
            b'--boundary\r\nContent-Disposition: form-data; name="email"\r\n\r\n'
            b"student@example.test +6281234567890 4111111111111111\r\n--boundary--\r\n"
        )
        content_type = "multipart/form-data; boundary=boundary"
    findings, complete = analyze(
        "example.test", "https://example.test", "", body, content_type, encoding, [], set()
    )
    assert complete
    assert {f.label for f in findings} == {"email", "phone_id", "payment_card"}
    assert not any(value in str(findings) for value in DUMMY.values())


def test_url_headers_and_invalid_cards():
    findings, complete = analyze(
        "example.test",
        "https://example.test?q=a%40example.test",
        "X-Dummy: b@example.test",
        b"4111111111111112",
        "text/plain",
        "",
        [],
        set(),
    )
    assert complete
    assert {f.location for f in findings} == {"url", "headers"}


@pytest.mark.parametrize("kind", ["binary", "utf8", "oversize", "gzip_bomb", "br"])
def test_unsupported_content_does_not_silently_pass(kind):
    bodies = {
        "binary": (b"binary", "image/png", ""),
        "utf8": (b"\xff", "text/plain", ""),
        "oversize": (b"x" * 256001, "text/plain", ""),
        "gzip_bomb": (gzip.compress(b"x" * 1_000_000), "text/plain", "gzip"),
        "br": (b"compressed", "text/plain", "br"),
    }
    body, content_type, encoding = bodies[kind]
    findings, complete = analyze(
        "example.test", "https://example.test", "", body, content_type, encoding, [], set()
    )
    assert not complete
    assert "inspection_incomplete" in {f.label for f in findings}


def test_large_plain_text_scan_has_bounded_runtime():
    started = time.monotonic()
    findings, complete = analyze(
        "example.test", "http://example.test", "", b"x" * 256000, "text/plain", "", [], set()
    )
    assert complete and not findings
    assert time.monotonic() - started < 2
    assert decode_body(b"not json", "application/json", "")[1] is False
