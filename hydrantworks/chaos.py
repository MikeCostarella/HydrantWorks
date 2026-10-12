"""Chaos mode: make the read API unreliable on purpose, so agents can be hardened against it.

Set HW_CHAOS to a comma-separated list, for example

    HW_CHAOS=latency=2.0,error_rate=0.2,empty_rate=0.1

  latency=S        add up to S seconds of random delay to each read
  error_rate=P     fail a read with HTTP 503 with probability P
  empty_rate=P     answer a list read with an empty page with probability P
  timeout_rate=P   stall a read for 30 seconds with probability P

HW_CHAOS_SEED makes the sequence repeatable. Only GET requests to /hydrants,
/inspections and /work-orders are affected; /health and writes never are.
"""

from __future__ import annotations

import asyncio
import json
import random

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

AFFECTED = ("/hydrants", "/inspections", "/work-orders")


def parse_chaos(spec: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in filter(None, (p.strip() for p in spec.split(","))):
        key, _, value = part.partition("=")
        out[key.strip()] = float(value)
    return out


class ChaosMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, spec: str, seed: int | None = None):
        super().__init__(app)
        self.cfg = parse_chaos(spec)
        self.rng = random.Random(seed)

    async def dispatch(self, request: Request, call_next):
        if request.method != "GET" or not request.url.path.startswith(AFFECTED):
            return await call_next(request)
        cfg, rng = self.cfg, self.rng
        if cfg.get("latency"):
            await asyncio.sleep(rng.uniform(0, cfg["latency"]))
        if rng.random() < cfg.get("timeout_rate", 0):
            await asyncio.sleep(30)
        if rng.random() < cfg.get("error_rate", 0):
            return JSONResponse({"detail": "Service temporarily unavailable (chaos mode)."}, status_code=503)
        response = await call_next(request)
        if rng.random() < cfg.get("empty_rate", 0) and response.status_code == 200:
            body = b"".join([chunk async for chunk in response.body_iterator])
            data = json.loads(body)
            if isinstance(data, dict) and "items" in data:
                data.update(items=[], total=0)
                return JSONResponse(data, status_code=200)
            return Response(body, status_code=response.status_code, headers=dict(response.headers))
        return response
