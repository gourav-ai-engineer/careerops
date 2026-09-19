from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from app.settings import settings

logger = logging.getLogger("careerops")


async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed request_id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_completed request_id=%s method=%s path=%s status=%s duration_ms=%s", request_id, request.method, request.url.path, response.status_code, elapsed_ms)
    return response


async def api_key_middleware(request: Request, call_next):
    if not settings.api_key:
        return await call_next(request)
    if request.method == "OPTIONS" or request.url.path in {"/", "/health", "/health/db", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
        return await call_next(request)
    if request.headers.get("X-API-Key") != settings.api_key:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)
