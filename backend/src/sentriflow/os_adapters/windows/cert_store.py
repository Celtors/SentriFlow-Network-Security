import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from mitmproxy.certs import CertStore

from sentriflow.os_adapters.windows.file_acl import restrict_private_directory


def prepare_ca(ca_dir: Path) -> Path:
    restrict_private_directory(ca_dir)
    CertStore.from_store(ca_dir, "mitmproxy", 2048)
    return ca_dir / "mitmproxy-ca-cert.cer"


def thumbprint(ca_dir: Path) -> str | None:
    certificate = ca_dir / "mitmproxy-ca-cert.pem"
    if not certificate.exists():
        return None
    cert = x509.load_pem_x509_certificate(certificate.read_bytes())
    return cert.fingerprint(hashes.SHA1()).hex().upper()


def ca_status(ca_dir: Path) -> dict[str, object]:
    fingerprint = thumbprint(ca_dir)
    trusted = False
    if fingerprint and sys.platform == "win32":
        result = subprocess.run(
            ["certutil", "-user", "-store", "Root", fingerprint], capture_output=True, timeout=15
        )
        trusted = result.returncode == 0
    return {
        "generated": fingerprint is not None,
        "trusted": trusted,
        "thumbprint": fingerprint,
        "supported": sys.platform == "win32",
    }


def install_ca(ca_dir: Path, *, confirmed: bool) -> dict[str, object]:
    if not confirmed:
        raise ValueError("Installing the local CA requires explicit consent")
    if sys.platform != "win32":
        raise OSError("Current-user certificate installation requires Windows")
    certificate = prepare_ca(ca_dir)
    subprocess.run(
        ["certutil", "-user", "-addstore", "Root", str(certificate)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return ca_status(ca_dir)


def remove_ca(ca_dir: Path) -> dict[str, object]:
    fingerprint = thumbprint(ca_dir)
    if sys.platform != "win32":
        raise OSError("Current-user certificate removal requires Windows")
    if fingerprint:
        subprocess.run(
            ["certutil", "-user", "-delstore", "Root", fingerprint],
            check=True,
            capture_output=True,
            timeout=30,
        )
    return ca_status(ca_dir)
