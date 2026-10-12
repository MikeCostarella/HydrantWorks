"""Request tracing: every request gets a trace id, echoed back and logged.

Send X-Trace-Id to correlate the service's log with your own agent's trace;
otherwise the service makes one up. Each request writes one JSON line to the
log (stdout, and HW_REQUEST_LOG if set).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = logging.getLogger("hydrantworks.requests")


class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, log_path: Path | None = None):
        super().__init__(app)
        self.log_path = log_path

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
        request.state.trace_id = trace_id
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            line = json.dumps(
                {
                    "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query),
                    "status": status,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
            log.info(line)
            if self.log_path:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
