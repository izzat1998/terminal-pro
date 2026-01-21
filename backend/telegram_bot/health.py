"""
Health check endpoints for Telegram Bot webhook server.

Provides /bot/health and /bot/ready endpoints for monitoring and orchestration.
"""

import logging
from datetime import datetime, timezone

from aiohttp import web


logger = logging.getLogger(__name__)

# Track server start time for uptime calculation
_start_time: datetime | None = None


def set_start_time() -> None:
    """Set the server start time. Called once on startup."""
    global _start_time
    _start_time = datetime.now(timezone.utc)


async def health_check(request: web.Request) -> web.Response:
    """
    Basic health check endpoint.

    Returns 200 OK if the server is running.
    Used by nginx/load balancers to check if the service is alive.

    Endpoint: GET /bot/health
    """
    global _start_time

    if _start_time is None:
        set_start_time()

    uptime_seconds = (datetime.now(timezone.utc) - _start_time).total_seconds()

    return web.json_response(
        {
            "status": "ok",
            "mode": "webhook",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": int(uptime_seconds),
        },
        status=200,
    )


async def readiness_check(request: web.Request) -> web.Response:
    """
    Readiness check endpoint.

    Verifies the service is ready to handle requests.
    Checks Redis connectivity for FSM storage.

    Endpoint: GET /bot/ready
    """
    import os

    checks = {
        "redis": False,
        "django": False,
    }

    # Check Redis connectivity
    try:
        from redis.asyncio import Redis

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))

        redis = Redis(host=redis_host, port=redis_port)
        await redis.ping()
        await redis.close()
        checks["redis"] = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        checks["redis"] = False

    # Check Django database connectivity
    try:
        from asgiref.sync import sync_to_async
        from django.db import connection

        @sync_to_async
        def check_db():
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()

        await check_db()
        checks["django"] = True
    except Exception as e:
        logger.warning(f"Django DB health check failed: {e}")
        checks["django"] = False

    # Determine overall status
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return web.json_response(
        {
            "status": "ready" if all_healthy else "degraded",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status=status_code,
    )
