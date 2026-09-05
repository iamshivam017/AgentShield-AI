import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from app.api.routes import audit, auth, policies, risk, webhooks
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base, SessionLocal, engine
from app.db.seed import seed_demo_data

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
REQUESTS = Counter("agentshield_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("agentshield_http_request_seconds", "HTTP request latency", ["method", "path"])
rate_windows: defaultdict[str, deque[float]] = defaultdict(deque)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.environment in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_demo_data(db, settings.demo_user_password)
    # Warm the ML model on startup through its first real request in production to
    # keep health checks fast. Benchmarks remain independently reproducible.
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Bounded risk decisions for agent-initiated payments",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Razorpay-Signature"],
)


@app.middleware("http")
async def safety_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:64]
    now = time.monotonic()
    client = request.client.host if request.client else "unknown"
    window = rate_windows[client]
    while window and window[0] < now - 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        return JSONResponse(
            status_code=429, content={"detail": "Rate limit exceeded", "request_id": request_id}
        )
    window.append(now)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled request failure", extra={"request_id": request_id, "event": "http.error"}
        )
        response = JSONResponse(
            status_code=500, content={"detail": "Internal server error", "request_id": request_id}
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    elapsed = time.perf_counter() - started
    matched_route = request.scope.get("route")
    route = getattr(matched_route, "path", "unmatched")
    REQUESTS.labels(request.method, route, response.status_code).inc()
    LATENCY.labels(request.method, route).observe(elapsed)
    return response


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def ready() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT count(*) FROM users"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )
    return JSONResponse(content={"status": "ready"})


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


for router in (auth.router, risk.router, policies.router, audit.router, webhooks.router):
    app.include_router(router, prefix="/api/v1")
