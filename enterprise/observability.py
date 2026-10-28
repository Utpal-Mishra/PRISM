from __future__ import annotations

import hmac
import json
import logging
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from enterprise.config import EnterpriseSettings, get_settings

LOGGER = logging.getLogger("prism.enterprise")

REQUESTS = Counter(
    "prism_http_requests_total",
    "PRISM Enterprise HTTP requests.",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "prism_http_request_duration_seconds",
    "PRISM Enterprise HTTP request latency.",
    ["method", "route"],
)
JOBS = Counter(
    "prism_jobs_total",
    "PRISM Enterprise job terminal outcomes.",
    ["job_type", "status"],
)
CONNECTOR_RUNS = Counter(
    "prism_connector_runs_total",
    "PRISM Enterprise connector run outcomes.",
    ["connector_type", "status"],
)
MATERIALIZATIONS = Counter(
    "prism_materializations_total",
    "PRISM governed dataset materialisation outcomes.",
    ["status"],
)
DECISION_CASES = Counter(
    "prism_decision_cases_total",
    "PRISM AI Control Plane decision-case outcomes.",
    ["status"],
)


def _route_label(request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def install_observability(
    app: FastAPI,
    settings: EnterpriseSettings | None = None,
) -> None:
    settings = settings or get_settings()

    @app.middleware("http")
    async def observe_requests(request, call_next):
        started = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        route = _route_label(request)
        duration = time.perf_counter() - started
        REQUESTS.labels(
            method=request.method,
            route=route,
            status=str(response.status_code),
        ).inc()
        LATENCY.labels(method=request.method, route=route).observe(duration)
        LOGGER.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
                separators=(",", ":"),
            )
        )
        return response

    @app.get("/metrics", include_in_schema=False)
    def metrics(x_prism_metrics_token: str | None = Header(default=None)) -> Response:
        configured = settings.metrics_token.get_secret_value()
        if configured and not hmac.compare_digest(
            configured,
            x_prism_metrics_token or "",
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Metrics authentication is required.",
            )
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get("/health/slo")
    def slo() -> dict[str, float | int]:
        return {
            "availability_target": settings.slo_availability_target,
            "latency_p95_ms_target": settings.slo_latency_p95_ms,
        }
