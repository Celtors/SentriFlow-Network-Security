import os
import subprocess
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes


def certificate_status(ca_dir: Path) -> dict[str, str | bool | None]:
    public = ca_dir / "mitmproxy-ca-cert.pem"
    thumbprint = None
    if public.exists():
        certificate = x509.load_pem_x509_certificate(public.read_bytes())
        thumbprint = certificate.fingerprint(hashes.SHA1()).hex().upper()
    return {
        "generated": public.exists(),
        "public_certificate": str(public),
        "thumbprint": thumbprint,
        "trust_status": "not_checked",
    }


def manage_ca(ca_dir: Path, install: bool) -> None:
    if os.name != "nt":
        raise RuntimeError("Certificate store integration requires Windows")
    status = certificate_status(ca_dir)
    if not status["generated"]:
        raise ValueError("Start the proxy once to generate its CA certificate")
    args = (
        ["certutil", "-user", "-addstore", "Root", str(ca_dir / "mitmproxy-ca-cert.cer")]
        if install
        else ["certutil", "-user", "-delstore", "Root", str(status["thumbprint"])]
    )
    subprocess.run(args, check=True, capture_output=True)
