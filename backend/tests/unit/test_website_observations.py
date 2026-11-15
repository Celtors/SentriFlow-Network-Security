import gzip
import json

import pytest

from sentriflow.website.observations import HTML_LIMIT, HtmlObservation


@pytest.mark.parametrize("compressed", [False, True])
def test_form_structure_without_sensitive_values(compressed):
    body = (
        b'<form action="https://collector.example.net/save?token=private-value">'
        b'<input type="password" name="secret-name" value="private-value">'
        b'<input type="email" value="private-value"></form>'
    )
    headers = {"content-type": "text/html; charset=utf-8"}
    if compressed:
        headers["content-encoding"] = "gzip"
        body = gzip.compress(body)
    observation = HtmlObservation("example.com", headers)
    for i in range(0, len(body), 9):
        observation.feed(body[i : i + 9])
    result = observation.finish()
    assert result["forms"] == 1 and result["password_fields"] == 1
    assert result["email_fields"] == 1
    assert result["external_form_domains"] == ["collector.example.net"]
    assert "private-value" not in json.dumps(result)
    assert "secret-name" not in json.dumps(result)
    assert observation.parser is None


def test_decompression_bomb_is_bounded_and_partial():
    observation = HtmlObservation(
        "example.com", {"content-type": "text/html", "content-encoding": "gzip"}
    )
    observation.feed(gzip.compress(b"a" * (HTML_LIMIT * 20)))
    result = observation.finish()
    assert result["sample_bytes"] == HTML_LIMIT
    assert result["partial"]


def test_unsupported_disabled_and_corrupt_html_are_unavailable():
    for headers, enabled in [
        ({"content-type": "text/html", "content-encoding": "br"}, True),
        ({"content-type": "text/html"}, False),
        ({"content-type": "image/png"}, True),
    ]:
        observation = HtmlObservation("example.com", headers, enabled=enabled)
        observation.feed(b'<input type="password">')
        assert observation.finish()["state"] == "unavailable"
    corrupt = HtmlObservation(
        "example.com", {"content-type": "text/html", "content-encoding": "gzip"}
    )
    corrupt.feed(b"not-compressed")
    assert corrupt.finish()["state"] == "unavailable"


def test_base_and_formaction_domains():
    observation = HtmlObservation("example.com", {"content-type": "text/html"})
    observation.feed(
        b'<base href="https://other.example.net/private"><form action="/send">'
        b'<button formaction="https://override.example.org/post">Send</button></form>'
    )
    assert observation.finish()["external_form_domains"] == [
        "other.example.net",
        "override.example.org",
    ]
