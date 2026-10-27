"""Conservative redaction, including names, tokens and path segments."""


def mask_sample(value: str) -> str:
    return "[redacted]"


def mask_path(path: str) -> str:
    return "/" if path in ("", "/") else "/[redacted]"
