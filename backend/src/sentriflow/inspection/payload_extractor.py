"""Bounded, ephemeral extraction. No values returned here are persisted."""

import json
import zlib
from collections.abc import Mapping
from urllib.parse import unquote_plus

from sentriflow.constants import MAX_INSPECTION_BYTES


class InspectionLimit(ValueError):
    pass


def extract_parts(
    url: str, headers: Mapping[str, str], body: bytes, limit: int = MAX_INSPECTION_BYTES
) -> list[tuple[str, str]]:
    header_text = "\n".join(f"{k}: {v}" for k, v in headers.items())
    if len(url) + len(header_text) > limit or len(body) > limit:
        raise InspectionLimit("Request exceeds inspection limit")
    parts = [("url", unquote_plus(url)), ("headers", header_text)]
    encoding = headers.get("content-encoding", "").lower()
    if encoding in ("gzip", "deflate"):
        try:
            decoder = zlib.decompressobj(31 if encoding == "gzip" else 15)
            body = decoder.decompress(body, limit + 1)
            if len(body) > limit or decoder.unconsumed_tail or not decoder.eof:
                raise InspectionLimit(
                    "Compressed request exceeds inspection limit or is incomplete"
                )
        except zlib.error as error:
            raise InspectionLimit("Cannot decode compressed request") from error
    elif encoding and encoding != "identity":
        raise InspectionLimit("Unsupported request encoding")
    content_type = headers.get("content-type", "").lower()
    textual = (
        not content_type
        or content_type.startswith("text/")
        or any(kind in content_type for kind in ("json", "xml", "form", "javascript"))
    )
    if body and not textual:
        raise InspectionLimit("Binary request body is not inspected")
    if body:
        text = body.decode("utf-8", errors="replace")
        if "json" in content_type:
            try:
                # JSON serialization decodes escaped letters and unicode before matching.
                text = json.dumps(json.loads(text), ensure_ascii=False)
            except (ValueError, RecursionError) as error:
                raise InspectionLimit("Invalid JSON request") from error
        parts.append(("body", unquote_plus(text) if "urlencoded" in content_type else text))
    return parts
