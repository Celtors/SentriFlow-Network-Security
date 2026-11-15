"""Live summaries. URLs and headers are used transiently, never retained in this service."""

import asyncio
import copy
import logging
from collections import OrderedDict
from uuid import uuid4

from sentriflow.core.events import EventBus
from sentriflow.core.models import Flow, Verdict, utc_now
from sentriflow.ml.features import canonical_origin, host_from_url, registered_domain
from sentriflow.ml.predictor import Predictor

logger = logging.getLogger(__name__)
MAX_SITES = 50
MAX_LINKS = 1000


def unavailable_evidence():
    return {
        "browser_information": {
            "state": "not_observed",
            "detail": "No browser headers observed yet.",
        },
        "cookies": {"state": "not_observed", "detail": "Cookie values are never retained."},
        "forms": {"state": "unavailable", "detail": "No inspectable HTML response observed yet."},
        "permissions": {
            "state": "unavailable",
            "detail": "Camera, microphone and location "
            "permission attempts/results are not observable through this proxy.",
        },
        "fingerprinting": {
            "state": "unavailable",
            "detail": "Canvas, WebGL, screen resolution "
            "and JavaScript device API execution require browser telemetry.",
        },
        "browser_storage": {
            "state": "unavailable",
            "detail": "Local/session storage reads "
            "and JavaScript cookie access are not observable here.",
        },
    }


class WebsiteMonitor:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.model: Predictor | None = None
        self.model_error = "Model has not loaded yet"
        self.sites: OrderedDict[str, dict] = OrderedDict()
        self.links: OrderedDict[str, dict] = OrderedDict()
        self.current_id: str | None = None
        self._inference_slots = asyncio.Semaphore(2)

    async def open(self):
        try:
            self.model = await asyncio.to_thread(Predictor)
            self.model_error = ""
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            self.model = None
            self.model_error = (
                "Trained model is missing, invalid or incompatible; no estimate available."
            )
            logger.warning("Website risk model unavailable; traffic controls remain active")

    def status(self):
        return (
            self.model.status() if self.model else {"available": False, "reason": self.model_error}
        )

    def snapshot(self):
        return {
            "websites": [copy.deepcopy(s) for s in reversed(self.sites.values())],
            "current_website_id": self.current_id,
            "website_model": self.status(),
        }

    def emit(self, site: dict):
        site["updated_at"] = utc_now().isoformat()
        self.bus.publish(
            "website.updated",
            {"website": copy.deepcopy(site), "current_website_id": self.current_id},
        )

    async def observe_request(self, flow: Flow, url: str, headers: dict[str, str]):
        host = host_from_url(url)
        if host is None:
            return
        navigation = (
            headers.get("sec-fetch-dest") == "document"
            and headers.get("sec-fetch-mode") == "navigate"
        )
        referrer = host_from_url(headers.get("referer", ""))
        origin = host_from_url(headers.get("origin", ""))
        page_host = referrer or origin
        site = None
        if not navigation:
            for candidate in reversed(self.sites.values()):
                if candidate["process_key"] == flow.process_key and candidate["host"] == (
                    page_host or host
                ):
                    site = candidate
                    break
        if site is None:
            site = {
                "id": uuid4().hex,
                "host": host,
                "scheme": flow.scheme,
                "process_name": flow.process_name,
                "process_key": flow.process_key,
                "identified_by": "page_navigation" if navigation else "observed_destination",
                "first_seen": utc_now().isoformat(),
                "updated_at": utc_now().isoformat(),
                "analysis": {
                    "state": "analyzing",
                    "maliciousness_percentage": None,
                    "risk_level": "unknown",
                    "reasons": [],
                },
                "evidence": unavailable_evidence(),
                "requests": 0,
                "blocked_requests": 0,
                "completed_requests": 0,
                "third_party_requests": 0,
                "external_domains": [],
                "redirect_domains": [],
                "redirects": 0,
                "tls_status": flow.tls_status,
                "bytes_up": 0,
                "bytes_down": 0,
                "association_note": "Most recent observed page, not the focused tab. "
                "Related requests use referrer/Origin host and process; "
                "multiple tabs of the same host cannot be distinguished.",
            }
            self.sites[site["id"]] = site
            if (
                navigation
                or self.current_id is None
                or (self.sites.get(self.current_id, {}).get("identified_by") != "page_navigation")
            ):
                self.current_id = site["id"]
            while len(self.sites) > MAX_SITES:
                oldest = next(iter(self.sites))
                if oldest == self.current_id:
                    self.sites.move_to_end(oldest)
                else:
                    del self.sites[oldest]
            self.emit(site)
            try:
                if self.model:
                    async with self._inference_slots:
                        site["analysis"] = await asyncio.to_thread(
                            self.model.analyze, canonical_origin(url) or ""
                        )
                else:
                    site["analysis"] = {
                        "state": "unavailable",
                        "reason": self.model_error,
                        "maliciousness_percentage": None,
                        "risk_level": "unknown",
                        "reasons": [],
                    }
            except (ValueError, OverflowError, KeyError, TypeError, IndexError):
                site["analysis"] = {
                    "state": "error",
                    "reason": "Website estimate unavailable.",
                    "maliciousness_percentage": None,
                    "risk_level": "unknown",
                    "reasons": [],
                }
                logger.warning("Website inference failed; no estimate emitted")
        site["requests"] += 1
        browser_headers = any(
            name in headers
            for name in ("user-agent", "sec-ch-ua", "sec-ch-ua-platform", "sec-ch-ua-mobile")
        )
        cookie = "cookie" in headers
        self.links[flow.id] = {
            "site": site["id"],
            "browser_headers": browser_headers,
            "cookie": cookie,
            "page": navigation or (not headers.get("sec-fetch-dest") and not page_host),
        }
        while len(self.links) > MAX_LINKS:
            self.links.popitem(last=False)
        if browser_headers:
            self._header_evidence(site, "browser_information", False)
        if cookie:
            self._header_evidence(site, "cookies", False)
        if page_host and registered_domain(host) != registered_domain(site["host"]):
            site["third_party_requests"] += 1
            if host not in site["external_domains"] and len(site["external_domains"]) < 40:
                site["external_domains"].append(host)
        self.emit(site)

    def _header_evidence(self, site, key, transmitted):
        previous = site["evidence"][key]
        observed = transmitted or previous["state"] == "transmission_observed"
        site["evidence"][key] = {
            "state": "transmission_observed" if observed else "access_attempt",
            "detail": (
                "Header presence observed in a forwarded request with an upstream response. "
                "This does not prove the recipient stored/read it."
                if observed
                else "Header presence observed before forwarding; delivery is not established."
            ),
            "values_retained": False,
            "recipient_access_confirmed": False,
        }

    def observe_response(self, flow: Flow, headers: dict[str, str]):
        link = self.links.get(flow.id)
        site = self.sites.get(link["site"]) if link else None
        if site is None or flow.verdict != Verdict.ALLOW:
            return
        if link["browser_headers"]:
            self._header_evidence(site, "browser_information", True)
        if link["cookie"]:
            self._header_evidence(site, "cookies", True)
        if "set-cookie" in headers:
            site["evidence"]["cookie_response"] = {
                "state": "collection_observed",
                "detail": "Set-Cookie header observed in response; "
                "browser acceptance/storage is unknown. Names and values are discarded.",
            }
        if flow.status_code and 300 <= flow.status_code < 400:
            site["redirects"] += 1
            target = host_from_url(headers.get("location", ""))
            if (
                target
                and target not in site["redirect_domains"]
                and len(site["redirect_domains"]) < 20
            ):
                site["redirect_domains"].append(target)
        self.emit(site)

    def observe_html(self, flow: Flow, observation: dict):
        link = self.links.get(flow.id)
        site = self.sites.get(link["site"]) if link else None
        # Only page responses affect form evidence, not every image/script/resource.
        if site and flow.host == site["host"] and link.get("page"):
            site["evidence"]["forms"] = observation
            self.emit(site)

    def complete(self, flow: Flow):
        link = self.links.pop(flow.id, None)
        site = self.sites.get(link["site"]) if link else None
        if site:
            site["completed_requests"] += 1
            site["blocked_requests"] += int(flow.verdict == Verdict.BLOCK)
            site["bytes_up"] += flow.bytes_up if flow.verdict == Verdict.ALLOW else 0
            site["bytes_down"] += flow.bytes_down
            self.emit(site)
