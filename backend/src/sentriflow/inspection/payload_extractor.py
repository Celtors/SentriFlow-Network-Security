import json
import zlib
from email import policy
from email.parser import BytesParser
from urllib.parse import unquote_plus

MAX_SCAN = 256_000


def decode_body(body: bytes, content_type: str, encoding: str) -> tuple[str, bool]:
    if not body:
        return "", True
    if len(body) > MAX_SCAN:
        return "", False
    try:
        if encoding.lower() in ("gzip", "deflate"):
            decoder = zlib.decompressobj(
                16 + zlib.MAX_WBITS if encoding == "gzip" else zlib.MAX_WBITS
            )
            body = decoder.decompress(body, MAX_SCAN + 1)
            if len(body) > MAX_SCAN or not decoder.eof or decoder.unused_data:
                return "", False
        elif encoding.lower() not in ("", "identity"):
            return "", False
        media = content_type.split(";", 1)[0].strip().lower()
        if media == "multipart/form-data":
            message = BytesParser(policy=policy.default).parsebytes(
                f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
            )
            if not message.is_multipart() or message.defects:
                return "", False
            parts = []
            for part in message.iter_parts():
                if part.get_filename() or part.is_multipart():
                    return "", False
                payload = part.get_payload(decode=True)
                if not isinstance(payload, bytes):
                    return "", False
                parts.append(payload.decode("utf-8"))
            return "\n".join(parts), True
        if not (
            media.startswith("text/")
            or media in ("application/json", "application/xml", "application/x-www-form-urlencoded")
            or media.endswith("+json")
        ):
            return "", False
        text = body.decode("utf-8")
        if media == "application/json" or media.endswith("+json"):
            # Decode escaped values before matching, never write this temporary representation.
            text = json.dumps(json.loads(text), ensure_ascii=False)
        if media == "application/x-www-form-urlencoded":
            text = unquote_plus(text)
        return text, True
    except (ValueError, UnicodeError, zlib.error):
        return "", False
