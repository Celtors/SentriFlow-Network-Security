"""Response metadata inspection without retaining raw HTML or form values."""

import codecs
import zlib
from html.parser import HTMLParser
from urllib.parse import urljoin

from sentriflow.ml.features import host_from_url, registered_domain

HTML_LIMIT = 131072
WIRE_LIMIT = 262144


class FormParser(HTMLParser):
    def __init__(self, host: str):
        super().__init__(convert_charrefs=True)
        self.host = host
        self.base_origin = f"https://{host}/"
        self.forms = 0
        self.password_fields = 0
        self.email_fields = 0
        self.external_form_domains: set[str] = set()

    def handle_starttag(self, tag, attrs):
        # Never read input values, names, script content or text nodes.
        attributes = dict(attrs)
        if tag == "base" and attributes.get("href"):
            target = host_from_url(urljoin(self.base_origin, attributes["href"]))
            if target:
                self.base_origin = f"https://{target}/"
        if tag == "form":
            self.forms += 1
        if tag in {"form", "button", "input"}:
            action = attributes.get("action") if tag == "form" else attributes.get("formaction")
            if action:
                target = host_from_url(urljoin(self.base_origin, action))
                if target and registered_domain(target) != registered_domain(self.host):
                    if len(self.external_form_domains) < 20:
                        self.external_form_domains.add(target)
        if tag == "input":
            kind = (attributes.get("type") or "text").lower()
            self.password_fields += int(kind == "password")
            self.email_fields += int(kind == "email")


class HtmlObservation:
    """Streaming bounded tee: all original bytes must still be forwarded unchanged.

    Handles identity and gzip/deflate with a strict decompressed cap; unsupported
    encodings/charsets remain unavailable. No response body is retained after finish.
    """

    def __init__(self, host: str, headers: dict[str, str], *, enabled: bool = True):
        content_type = headers.get("content-type", "").lower()
        encoding = headers.get("content-encoding", "identity").lower().strip()
        self.reason = "Response is not HTML"
        self.parser = FormParser(host)
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.unzip = None
        self.available = "text/html" in content_type
        if not enabled:
            self.available = False
            self.reason = "Content inspection is disabled"
        if "charset=" in content_type and not any(
            x in content_type for x in ("utf-8", "utf8", "us-ascii")
        ):
            self.available = False
            self.reason = "HTML character encoding is unsupported"
        if encoding in {"gzip", "deflate"}:
            self.unzip = zlib.decompressobj(31 if encoding == "gzip" else 15)
        elif encoding not in {"", "identity"}:
            self.available = False
            self.reason = "HTML compression is unsupported"
        self.wire_bytes = 0
        self.decoded_bytes = 0
        self.truncated = False
        self.failed = False
        self.finished = False

    def feed(self, chunk: bytes):
        if not self.available or self.failed or self.truncated or self.finished:
            return
        self.wire_bytes += len(chunk)
        if self.wire_bytes > WIRE_LIMIT:
            self.truncated = True
        try:
            remaining = HTML_LIMIT - self.decoded_bytes
            data = self.unzip.decompress(chunk, remaining + 1) if self.unzip else chunk
            if len(data) > remaining:
                self.truncated = True
                data = data[:remaining]
            self.decoded_bytes += len(data)
            self.parser.feed(self.decoder.decode(data))
        except (ValueError, AssertionError, zlib.error):
            self.failed = True
            self.reason = "HTML sample could not be decoded"

    def finish(self) -> dict:
        self.finished = True
        if not self.available or self.failed:
            self.parser = None
            self.unzip = None
            return {"state": "unavailable", "detail": self.reason}
        try:
            self.parser.close()
        except (ValueError, AssertionError):
            self.parser = None
            self.unzip = None
            return {"state": "unavailable", "detail": "HTML sample could not be parsed"}
        if self.unzip and not self.unzip.eof:
            self.truncated = True
        result = {
            "state": "structure_observed",
            "forms": self.parser.forms,
            "password_fields": self.parser.password_fields,
            "email_fields": self.parser.email_fields,
            "external_form_domains": sorted(self.parser.external_form_domains),
            "sample_bytes": self.decoded_bytes,
            "partial": self.truncated,
            "detail": "Static HTML structure only; fields do not prove entry/submission. "
            "Scripts, rendered DOM and later dynamic forms are not inspected.",
        }
        # Drop parser buffers/start-tag text and compression state immediately.
        self.parser = None
        self.unzip = None
        return result
