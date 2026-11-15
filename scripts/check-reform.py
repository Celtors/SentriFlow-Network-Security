"""Offline real-browser + HTTPS proxy + shipped model + live UI verification.

Public-shaped fixture domains route only to loopback inside the test harness.
Never changes OS routing/CA trust, never visits dataset or external URLs.
"""

import argparse
import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright
from sentriflow.ml.predictor import Predictor
from sentriflow.verification import local_stack

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir", type=Path, default=ROOT / "docs/evidence/reform"
    )
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sentriflow-website-") as directory:
        async with local_stack(Path(directory), website_fixture=True) as stack:
            rt, api, _, _, received, _, _ = stack
            base = f"http://127.0.0.1:{rt.config.api_port}"
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    channel="msedge", headless=True
                )
                dashboard = await browser.new_page(
                    viewport={"width": 460, "height": 900}
                )
                errors = []
                dashboard.set_default_timeout(10000)
                dashboard.on("pageerror", lambda error: errors.append(str(error)))
                await dashboard.goto(f"{base}/#token={rt.token}")
                await dashboard.get_by_text("Guardian connected", exact=True).wait_for()
                print("Compact dashboard connected", flush=True)
                assert await dashboard.locator(".companion-shell").is_visible()
                await dashboard.get_by_text(
                    "Waiting for a website", exact=True
                ).wait_for()
                # Isolated browser context trusts only for this test; no OS trust changes.
                browsing = await browser.new_context(
                    proxy={"server": f"http://127.0.0.1:{rt.config.proxy_port}"},
                    ignore_https_errors=True,
                )
                page = await browsing.new_page()
                ordinary_url = "https://www.example.com/private?token=PRIVATE-FIXTURE"
                navigation_response = await page.goto(ordinary_url)
                assert navigation_response and navigation_response.status == 200, (
                    f"Fixture navigation status: {navigation_response.status if navigation_response else 'none'}"
                )
                print("HTTPS fixture opened through the real proxy", flush=True)
                await dashboard.get_by_role(
                    "heading", name="www.example.com", exact=True
                ).wait_for()
                async with asyncio.timeout(10):
                    while True:
                        state = (await api.get("/api/websites")).json()
                        site = next(
                            s
                            for s in state["websites"]
                            if s["id"] == state["current_website_id"]
                        )
                        if site["evidence"]["forms"]["state"] == "structure_observed":
                            break
                        await asyncio.sleep(0.05)
                expected = Predictor().analyze(ordinary_url)
                assert site["analysis"] == expected
                expected_text = f"{expected['maliciousness_percentage']:.1f}%"
                await (
                    dashboard.get_by_test_id("website-percentage")
                    .filter(has_text=expected_text)
                    .wait_for()
                )
                assert site["identified_by"] == "page_navigation"
                assert site["evidence"]["forms"]["password_fields"] == 1
                assert site["evidence"]["permissions"]["state"] == "unavailable"
                assert "PRIVATE-FIXTURE" not in json.dumps(state)
                await dashboard.screenshot(
                    path=str(args.evidence_dir / "compact.png"), full_page=True
                )
                # A real third-party request, attributed with only its referrer host.
                await page.evaluate(
                    "fetch('https://cdn.example.net/asset', {mode: 'no-cors'})"
                )
                await dashboard.get_by_role(
                    "button", name="Explore details", exact=False
                ).click()
                await dashboard.get_by_role(
                    "heading", name="Your data, with the evidence"
                ).wait_for()
                await dashboard.get_by_text(
                    "collector.example.net", exact=False
                ).wait_for()
                await dashboard.get_by_text(
                    "Cannot observe", exact=True
                ).first.wait_for()
                await dashboard.set_viewport_size({"width": 1440, "height": 1100})
                await dashboard.screenshot(
                    path=str(args.evidence_dir / "website-details.png"), full_page=True
                )
                await dashboard.get_by_text(
                    "How this estimate is made", exact=True
                ).click()
                await dashboard.get_by_text("host length", exact=True).wait_for()
                # A distinct address creates a genuinely different model result over WS.
                unusual_url = "https://verify-login-2024.security-confirmation.com/"
                await page.goto(unusual_url)
                await dashboard.get_by_role(
                    "heading",
                    name="verify-login-2024.security-confirmation.com",
                    exact=True,
                ).wait_for()
                second = Predictor().analyze(unusual_url)
                assert (
                    second["maliciousness_percentage"]
                    != expected["maliciousness_percentage"]
                )
                await dashboard.get_by_text("high risk", exact=True).wait_for()
                # Preserve initial compact behavior on small screens and authenticated pop-out.
                await dashboard.get_by_role(
                    "button", name="Compact view", exact=True
                ).click()
                async with dashboard.expect_popup() as popup_info:
                    await dashboard.get_by_role(
                        "button", name="Open small window", exact=True
                    ).click()
                popup = await popup_info.value
                await popup.get_by_text("Guardian connected", exact=True).wait_for()
                await popup.get_by_role(
                    "heading",
                    name="verify-login-2024.security-confirmation.com",
                    exact=True,
                ).wait_for()
                await popup.close()
                await dashboard.set_viewport_size({"width": 390, "height": 844})
                assert await dashboard.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                await dashboard.screenshot(
                    path=str(args.evidence_dir / "mobile-compact.png"), full_page=True
                )
                await dashboard.reload()
                await dashboard.get_by_role(
                    "heading",
                    name="verify-login-2024.security-confirmation.com",
                    exact=True,
                ).wait_for()
                assert await dashboard.locator(".companion-shell").is_visible()
                assert not errors, errors
                await browsing.close()
                await browser.close()
            final = (await api.get("/api/snapshot")).json()
            assert "PRIVATE-FIXTURE" not in json.dumps(final)
            report = {
                "measured_at": datetime.now(UTC).isoformat(),
                "model_id": expected["model_id"],
                "ordinary_percentage": expected["maliciousness_percentage"],
                "unusual_percentage": second["maliciousness_percentage"],
                "checks": [
                    "real_https_navigation",
                    "actual_shipped_model_inference",
                    "live_websocket_result",
                    "compact_default",
                    "expanded_privacy_details",
                    "static_form_structure",
                    "explicit_unobservable_browser_apis",
                    "no_sensitive_values_in_api",
                    "model_explanation_details",
                    "responsive_compact",
                    "authenticated_popup",
                    "reload_resynchronization",
                ],
                "origin_requests": len(received),
                "browser_errors": errors,
                "limitation": "Offline loopback fixture with public-shaped names; no external website labels "
                "or production accuracy measured. No OS routing or CA trust modified.",
            }
            (args.evidence_dir / "browser-report.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
