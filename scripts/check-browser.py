"""Real local UI/proxy smoke test. Install backend[browser]; Microsoft Edge must be installed."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--browser-path", type=Path, help="Optional local Chromium/Chrome executable"
    )
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "docs" / "evidence")
    parser.add_argument(
        "--public-map-check",
        action="store_true",
        help="Explicitly request example.com through the proxy to exercise real country mapping",
    )
    args = parser.parse_args()
    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    guardian = await asyncio.to_thread(
        subprocess.Popen,
        [
            sys.executable,
            "-m",
            "sentriflow",
            "run",
            "--data-dir",
            str(ROOT / ".runtime" / "browser-smoke" / uuid4().hex),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=flags,
    )
    origin = await asyncio.to_thread(
        subprocess.Popen,
        [sys.executable, "demo/test-server/server.py"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=flags,
    )
    try:
        token = None
        async with asyncio.timeout(20):
            while not token:
                line = await asyncio.to_thread(guardian.stdout.readline)
                if line.startswith("Session token: "):
                    token = line.split(": ", 1)[1].strip()
                elif line.startswith("Dashboard: "):
                    token = parse_qs(
                        urlsplit(line.split(": ", 1)[1].strip()).fragment
                    ).get("token", [None])[0]
                if guardian.poll() is not None:
                    raise RuntimeError(
                        "Guardian startup failed: " + guardian.stderr.read()
                    )
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(trust_env=False) as direct:
            async with asyncio.timeout(15):
                while True:
                    try:
                        if (
                            await direct.get(
                                "http://127.0.0.1:8787/api/health", headers=headers
                            )
                        ).status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(0.1)
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    **(
                        {"executable_path": str(args.browser_path)}
                        if args.browser_path
                        else {"channel": "msedge"}
                    ),
                    headless=True,
                )
                page = await browser.new_page(viewport={"width": 1440, "height": 1100})
                page.set_default_timeout(10000)
                errors = []
                external_browser_requests = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "request",
                    lambda request: (
                        external_browser_requests.append(request.url)
                        if request.url.startswith(("http:", "https:"))
                        and not request.url.startswith("http://127.0.0.1:8787/")
                        else None
                    ),
                )
                await page.goto("http://127.0.0.1:8787")
                await page.get_by_label("Session token", exact=True).fill(token)
                await page.get_by_role(
                    "button", name="Open dashboard", exact=True
                ).click()
                await page.get_by_text("Guardian connected", exact=True).wait_for()
                latencies, click_latencies, detection = [], [], []

                async def decide_in_browser(dialog, action, request):
                    await page.evaluate("""() => {
                        window.sentriflowDecisionClick = null;
                        document.addEventListener('click', () => {
                            window.sentriflowDecisionClick = performance.now();
                        }, {capture: true, once: true});
                    }""")
                    started = time.perf_counter()
                    await dialog.get_by_role("button", name=action, exact=True).click()
                    response = await request
                    latencies.append(round((time.perf_counter() - started) * 1000, 2))
                    click_latencies.append(
                        round(
                            await page.evaluate(
                                "performance.now() - window.sentriflowDecisionClick"
                            ),
                            2,
                        )
                    )
                    return response

                async with httpx.AsyncClient(
                    proxy="http://127.0.0.1:8080", trust_env=False, timeout=40
                ) as proxied:
                    for index in range(3):
                        request = asyncio.create_task(
                            proxied.post(
                                "http://127.0.0.1:9090/submit",
                                json={
                                    "email": "student@example.test",
                                    "phone": "+6281234567890",
                                    "card": "4111111111111111",
                                },
                            )
                        )
                        dialog = page.get_by_role("dialog")
                        await dialog.wait_for()
                        text = await dialog.inner_text()
                        assert "student@example.test" not in text
                        detection.append(
                            all(
                                value in text.lower()
                                for value in ("email", "mobile number", "payment card")
                            )
                        )
                        if index == 0:
                            await page.screenshot(
                                path=str(evidence / "halt.png"), full_page=True
                            )
                        if index == 2:
                            await dialog.get_by_role("checkbox").check()
                        action = "Allow transfer" if index == 1 else "Block transfer"
                        response = await decide_in_browser(dialog, action, request)
                        assert response.status_code == (200 if index == 1 else 403)
                        await dialog.wait_for(state="hidden")
                    await page.get_by_role("button", name="Rules", exact=True).click()
                    await page.get_by_role(
                        "heading", name="Remembered decisions"
                    ).wait_for()
                    await page.get_by_role("combobox").select_option("allow")
                    async with asyncio.timeout(5):
                        while (
                            await direct.get(
                                "http://127.0.0.1:8787/api/rules", headers=headers
                            )
                        ).json()[0]["action"] != "allow":
                            await asyncio.sleep(0.05)
                    await page.get_by_role("button", name="Delete", exact=True).click()
                    await page.get_by_text("No saved rules.", exact=False).wait_for()
                    # A second API client must update the already-open dashboard.
                    remote_rule = await direct.post(
                        "http://127.0.0.1:8787/api/rules",
                        headers=headers,
                        json={
                            "host_match": "sync.example.test",
                            "action": "block",
                            "process_name": "External client",
                        },
                    )
                    assert remote_rule.status_code == 201
                    await page.get_by_text("sync.example.test", exact=True).wait_for()
                    assert (
                        await direct.delete(
                            "http://127.0.0.1:8787/api/rules/"
                            + remote_rule.json()["id"],
                            headers=headers,
                        )
                    ).status_code == 204
                    await page.get_by_text("No saved rules.", exact=False).wait_for()

                    # Reloading must resynchronize an existing hold without releasing it.
                    reconnect_request = asyncio.create_task(
                        proxied.post(
                            "http://127.0.0.1:9090/submit",
                            json={
                                "email": "student@example.test",
                                "phone": "+6281234567890",
                                "card": "4111111111111111",
                            },
                        )
                    )
                    await page.get_by_role("dialog").wait_for()
                    await page.reload()
                    await page.get_by_text("Guardian connected", exact=True).wait_for()
                    restored = page.get_by_role("dialog")
                    await restored.wait_for()
                    assert not reconnect_request.done()
                    restored_text = (await restored.inner_text()).lower()
                    detection.append(
                        all(
                            label in restored_text
                            for label in ("email", "mobile number", "payment card")
                        )
                    )
                    assert (
                        await decide_in_browser(
                            restored, "Block transfer", reconnect_request
                        )
                    ).status_code == 403
                    await restored.wait_for(state="hidden")
                    await page.get_by_role(
                        "button", name="Settings", exact=True
                    ).click()
                    await page.get_by_role(
                        "heading", name="Inspection controls"
                    ).wait_for()
                    await page.get_by_label("Tracker action", exact=True).select_option(
                        "block"
                    )
                    await page.get_by_role(
                        "button", name="Save settings", exact=True
                    ).click()
                    await page.get_by_role(
                        "button", name="Overview", exact=True
                    ).click()
                    previous_processes = (
                        await direct.get(
                            "http://127.0.0.1:8787/api/processes", headers=headers
                        )
                    ).json()
                    previous_download = sum(p["bytes_down"] for p in previous_processes)
                    stream = asyncio.create_task(
                        proxied.get("http://127.0.0.1:9090/stream")
                    )
                    async with asyncio.timeout(4):
                        while True:
                            processes = (
                                await direct.get(
                                    "http://127.0.0.1:8787/api/processes",
                                    headers=headers,
                                )
                            ).json()
                            if sum(
                                p["bytes_down"] for p in processes
                            ) >= previous_download + 16384 and any(
                                process["download_bps"] > 0 for process in processes
                            ):
                                assert not stream.done()
                                break
                            await asyncio.sleep(0.05)
                    await page.screenshot(
                        path=str(evidence / "dashboard.png"), full_page=True
                    )
                    assert (await stream).status_code == 200
                    if args.public_map_check:
                        # No personal data, cookies, authentication or URL query is sent.
                        public = await proxied.get("http://example.com/")
                        assert public.status_code == 200
                    await page.get_by_role("button", name="Traffic", exact=True).click()
                    await page.get_by_role(
                        "button", name="View request to 127.0.0.1"
                    ).first.click()
                    await page.get_by_role("heading", name="Request details").wait_for()
                    await page.get_by_role(
                        "button", name="Close request details"
                    ).click()
                    await page.get_by_role("button", name="Alerts", exact=True).click()
                    await page.get_by_label("Alert severity").select_option("high")
                    await page.get_by_role(
                        "button", name="View request", exact=True
                    ).first.wait_for()
                    await page.screenshot(
                        path=str(evidence / "alerts.png"), full_page=True
                    )
                    await page.get_by_role("button", name="Map", exact=True).click()
                    await page.locator(".destination-map svg path").first.wait_for()
                    assert (
                        await page.locator(".destination-map svg path").count() >= 150
                    )
                    geo = (
                        await direct.get(
                            "http://127.0.0.1:8787/api/geo/destinations",
                            headers=headers,
                        )
                    ).json()
                    assert geo["unknown"]["local_or_private_ip"] >= 4
                    if args.public_map_check:
                        assert geo["available"] and len(geo["destinations"]) >= 1
                        await page.get_by_role(
                            "button",
                            name=geo["destinations"][0]["country_name"],
                            exact=False,
                        ).wait_for()
                    await page.screenshot(
                        path=str(evidence / "map.png"), full_page=True
                    )
                await page.set_viewport_size({"width": 390, "height": 844})
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                await page.screenshot(
                    path=str(evidence / "mobile-map.png"), full_page=True
                )
                assert not external_browser_requests, external_browser_requests
                assert not errors, errors
                await browser.close()
            snapshot = (
                await direct.get("http://127.0.0.1:8787/api/snapshot", headers=headers)
            ).json()
            dummy = [flow for flow in snapshot["flows"] if flow["method"] == "POST"]
            report = {
                "measured_at": datetime.now(UTC).isoformat(),
                "sample_requests": len(detection),
                "seeded_detection": detection,
                "attributed_requests": sum(bool(f["process_key"]) for f in dummy),
                "decision_roundtrip_ms": latencies,
                "decision_click_to_response_ms": click_latencies,
                "timing_method": "roundtrip includes Playwright action waiting; click timing starts at captured DOM click and ends after proxy response plus a browser evaluation roundtrip",
                "download_observed_before_completion": True,
                "ui_checks": [
                    "halt_once",
                    "remember",
                    "edit_rule",
                    "delete_rule",
                    "save_settings",
                    "mobile_layout",
                    "redacted_request_detail",
                    "high_priority_alerts",
                    "offline_vector_map",
                    "pending_halt_after_reload",
                    "cross_client_rule_sync",
                ],
                "public_map_check": args.public_map_check,
                "map_countries": [
                    country["country_code"] for country in geo["destinations"]
                ],
                "external_browser_requests": external_browser_requests,
                "limitations": "Small local dummy sample. No real CA/proxy/firewall changes made.",
            }
            (evidence / "local-demo-report.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            print(json.dumps(report, indent=2))
    finally:
        requests = [
            task
            for name in ("request", "reconnect_request", "stream")
            if isinstance((task := locals().get(name)), asyncio.Task)
        ]
        for task in requests:
            if not task.done():
                task.cancel()
        await asyncio.gather(*requests, return_exceptions=True)
        for process in (guardian, origin):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
