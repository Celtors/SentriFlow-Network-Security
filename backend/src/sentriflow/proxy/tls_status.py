from typing import Literal

TLSStatus = Literal["inspected", "pinned", "passthrough"]


def tls_status(scheme: str, failed: bool = False) -> TLSStatus:
    if failed:
        # Compatibility value: TLS failed; pinning is only one possible cause.
        return "pinned"
    return "inspected" if scheme == "https" else "passthrough"
