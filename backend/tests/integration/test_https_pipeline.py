import asyncio
import ipaddress
import ssl
from datetime import UTC, datetime, timedelta

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from sentriflow.core.models import Verdict
from sentriflow.proxy.process_resolver import ProcessResolver
from sentriflow.proxy.runner import create_master
from tests.integration.test_r4_pipeline import free_port, next_pending


async def test_trusted_local_https_decrypt_hold_release(runtime, tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "SentriFlow test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    public, private = tmp_path / "origin.pem", tmp_path / "origin-key.pem"
    public.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(public, private)
    received = []

    async def origin(reader, writer):
        try:
            headers = await reader.readuntil(b"\r\n\r\n")
            length = next(
                (
                    int(line.split(b":", 1)[1])
                    for line in headers.split(b"\r\n")
                    if line.lower().startswith(b"content-length:")
                ),
                0,
            )
            received.append(await reader.readexactly(length))
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK")
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    server = await asyncio.start_server(origin, "127.0.0.1", 0, ssl=context)
    port = server.sockets[0].getsockname()[1]
    await runtime.open()
    runtime.config.proxy_port = free_port()
    runtime.resolver = ProcessResolver(runtime.config.proxy_port)
    master = create_master(runtime)
    master.options.update(ssl_verify_upstream_trusted_ca=str(public))
    task = asyncio.create_task(master.run())
    try:
        async with asyncio.timeout(10):
            while not runtime.proxy_running:
                if task.done():
                    task.result()
                await asyncio.sleep(0.01)
        trusted = ssl.create_default_context(cafile=str(tmp_path / "ca" / "mitmproxy-ca-cert.pem"))
        async with httpx.AsyncClient(
            proxy=f"http://127.0.0.1:{runtime.config.proxy_port}",
            verify=trusted,
            trust_env=False,
            timeout=10,
        ) as client:
            for action, status in (("block", 403), ("allow", 200)):
                request = asyncio.create_task(
                    client.post(
                        f"https://127.0.0.1:{port}/", json={"email": "student@example.test"}
                    )
                )
                flow_id = await next_pending(runtime)
                assert not received
                assert runtime.halts.pending()[0].flow.tls_status == "inspected"
                await runtime.halts.resolve(flow_id, Verdict(action))
                assert (await request).status_code == status
            assert len(received) == 1
    finally:
        runtime.halts.shutdown()
        master.shutdown()
        await task
        server.close()
        await server.wait_closed()
        await runtime.close()
