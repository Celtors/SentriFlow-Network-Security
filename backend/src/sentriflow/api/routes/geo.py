import ipaddress
from typing import Annotated

from fastapi import APIRouter, Depends

from sentriflow.api.dependencies import runtime as get_runtime
from sentriflow.application import Runtime

router = APIRouter()


@router.get("/geo/destinations")
async def destinations(runtime: Annotated[Runtime, Depends(get_runtime)]):
    countries = {}
    unknown = {"no_observed_ip": 0, "local_or_private_ip": 0, "not_in_database": 0}
    records = await runtime.flows.list(limit=10000)
    for flow in records:
        if not flow.destination_ip:
            unknown["no_observed_ip"] += 1
            continue
        if not ipaddress.ip_address(flow.destination_ip).is_global:
            unknown["local_or_private_ip"] += 1
            continue
        # Re-read local data so existing captures can benefit from a database update on restart.
        result = runtime.geoip.lookup(flow.destination_ip)
        if not result:
            unknown["not_in_database"] += 1
            continue
        code, name = result
        row = countries.setdefault(
            code,
            {
                "country_code": code,
                "country_name": name,
                "requests": 0,
                "blocked": 0,
                "bytes_up": 0,
                "bytes_down": 0,
            },
        )
        row["requests"] += 1
        row["blocked"] += int(flow.verdict == "block")
        row["bytes_up"] += flow.bytes_up if flow.verdict == "allow" else 0
        row["bytes_down"] += flow.bytes_down
    return runtime.geoip.status() | {
        "destinations": sorted(countries.values(), key=lambda r: -r["requests"]),
        "unknown": unknown,
        "total_requests": len(records),
        "scope": "Most recent 10,000 retained requests; observed IPs only, no DNS lookups",
    }
