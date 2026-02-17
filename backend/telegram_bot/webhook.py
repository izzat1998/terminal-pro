"""
Telegram Bot Webhook Server

Runs as a separate aiohttp server for production deployment.
Receives webhook requests from Telegram and processes them via aiogram.

Usage:
    python manage.py run_telegram_webhook
"""

# ruff: noqa: E402  # Imports must come after django.setup()

import asyncio
import logging
import os
import sys

import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django before importing any Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terminal_app.settings")
django.setup()

import time

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from django.conf import settings


# Global deduplication cache at HTTP level
_processed_updates: dict[int, float] = {}
_dedup_lock = None


class DeduplicatingRequestHandler(SimpleRequestHandler):
    """
    Custom webhook handler that deduplicates updates at the HTTP level.
    Prevents duplicate processing when Telegram sends the same update multiple times.
    """

    async def handle(self, request: web.Request) -> web.Response:
        """Handle incoming webhook request with deduplication."""
        global _dedup_lock
        if _dedup_lock is None:
            _dedup_lock = asyncio.Lock()

        # Parse the update to get update_id
        try:
            data = await request.json()
            update_id = data.get("update_id")

            # DEBUG: Log the update type with message_id
            update_type = "unknown"
            msg_id = None
            user_id = None
            if "message" in data:
                msg = data["message"]
                text = msg.get("text", "")[:30] if msg.get("text") else ""
                msg_id = msg.get("message_id")
                user_id = msg.get("from", {}).get("id")
                update_type = f"message: {text}"
            elif "callback_query" in data:
                cb = data["callback_query"]
                cb_data = cb.get("data", "")[:30]
                msg_id = cb.get("message", {}).get("message_id")
                user_id = cb.get("from", {}).get("id")
                update_type = f"callback_query: {cb_data}"
            elif "edited_message" in data:
                msg = data["edited_message"]
                msg_id = msg.get("message_id")
                user_id = msg.get("from", {}).get("id")
                update_type = "edited_message"
            logger.info(f"INCOMING: update_id={update_id}, msg_id={msg_id}, user={user_id}, type={update_type}")
        except Exception:
            # If we can't parse, let the parent handle it
            return await super().handle(request)

        if update_id:
            current_time = time.time()

            async with _dedup_lock:
                # Clean old entries (older than 5 minutes)
                cutoff = current_time - 300
                old_ids = [uid for uid, ts in _processed_updates.items() if ts < cutoff]
                for uid in old_ids:
                    del _processed_updates[uid]

                # Check for duplicate
                if update_id in _processed_updates:
                    logger.info(f"HTTP-level skip: duplicate update_id={update_id}")
                    return web.Response(text="ok")  # Respond OK but don't process

                # Mark as processed
                _processed_updates[update_id] = current_time

        # Process the update
        return await super().handle(request)

from telegram_bot.handlers import (
    common,
    container_cabinet,
    customer,
    entry,
    exit,
    group_entry,
    manager_access,
)
from telegram_bot.handlers.common import fallback_router
from telegram_bot.health import health_check, readiness_check
from telegram_bot.middleware import ManagerAccessMiddleware, UpdateDeduplicationMiddleware


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_config():
    """Get webhook configuration from Django settings or environment"""
    return {
        "bot_token": getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        or os.getenv("TELEGRAM_BOT_TOKEN"),
        "webhook_url": getattr(settings, "TELEGRAM_WEBHOOK_URL", None)
        or os.getenv("TELEGRAM_WEBHOOK_URL"),
        "webhook_secret": getattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
        or os.getenv("TELEGRAM_WEBHOOK_SECRET"),
        "webhook_path": "/bot/webhook/",
        "host": "0.0.0.0",
        "port": int(
            getattr(settings, "TELEGRAM_WEBHOOK_PORT", None)
            or os.getenv("TELEGRAM_WEBHOOK_PORT", "8001")
        ),
    }


async def on_startup(bot: Bot, config: dict) -> None:
    """
    Register webhook with Telegram on server startup.

    Called automatically when the aiohttp app starts.
    """
    webhook_url = config["webhook_url"]
    webhook_secret = config["webhook_secret"]

    if not webhook_url:
        logger.error("TELEGRAM_WEBHOOK_URL not configured!")
        return

    logger.info(f"Setting webhook to: {webhook_url}")

    await bot.set_webhook(
        url=webhook_url,
        secret_token=webhook_secret,
        drop_pending_updates=True,  # Ignore messages sent while bot was offline
        allowed_updates=[
            "message",
            "callback_query",
            "edited_message",
        ],
    )

    # Verify webhook was set
    webhook_info = await bot.get_webhook_info()
    logger.info(f"Webhook info: url={webhook_info.url}, pending_count={webhook_info.pending_update_count}")

    if webhook_info.last_error_message:
        logger.warning(f"Webhook last error: {webhook_info.last_error_message}")


async def on_shutdown(bot: Bot) -> None:
    """
    Clean up on server shutdown.

    Optionally delete webhook (commented out to preserve during restarts).
    """
    logger.info("Shutting down webhook server...")

    # Uncomment to delete webhook on shutdown:
    # await bot.delete_webhook()

    await bot.session.close()
    logger.info("Bot session closed")


def create_dispatcher() -> Dispatcher:
    """
    Create and configure the aiogram Dispatcher.

    Sets up FSM storage (Redis or Memory) and registers all handlers.
    """
    # Setup storage (Redis if available, Memory otherwise)
    try:
        from redis.asyncio import Redis

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "1"))
        redis_password = os.getenv("REDIS_PASSWORD")

        redis = Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_password)
        storage = RedisStorage(redis)
        logger.info(f"Using Redis storage: {redis_host}:{redis_port}/{redis_db}")
    except Exception as e:
        logger.warning(f"Redis not available, using Memory storage: {e}")
        storage = MemoryStorage()

    # Create dispatcher
    dp = Dispatcher(storage=storage)

    # Register middleware
    # Deduplication middleware at dispatcher level to catch ALL updates before any processing
    dedup_middleware = UpdateDeduplicationMiddleware()
    dp.update.outer_middleware(dedup_middleware)
    dp.message.middleware(ManagerAccessMiddleware())
    dp.callback_query.middleware(ManagerAccessMiddleware())

    # Register handlers (order matters for security!)
    # See bot.py for detailed explanation of handler order
    dp.include_router(manager_access.router)
    dp.include_router(customer.router)
    dp.include_router(container_cabinet.router)
    dp.include_router(common.router)
    dp.include_router(entry.router)
    dp.include_router(exit.exit_router)
    dp.include_router(group_entry.router)  # Group message entry creation
    dp.include_router(fallback_router)  # MUST be LAST - catches unhandled callbacks

    logger.info("Dispatcher configured with all handlers")
    return dp


def create_app(bot: Bot, dp: Dispatcher, config: dict) -> web.Application:
    """
    Create the aiohttp web application.

    Sets up webhook handler, health checks, and lifecycle hooks.
    """
    app = web.Application()

    # Create webhook request handler with deduplication and secret token verification
    webhook_handler = DeduplicatingRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config["webhook_secret"],
        handle_in_background=True,  # Respond to Telegram immediately
    )

    # Register webhook endpoint
    webhook_handler.register(app, path=config["webhook_path"])
    logger.info(f"Webhook handler registered at: {config['webhook_path']}")

    # Register health check endpoints
    app.router.add_get("/bot/health", health_check)
    app.router.add_get("/bot/ready", readiness_check)
    logger.info("Health check endpoints registered: /bot/health, /bot/ready")

    # Setup aiogram lifecycle (startup/shutdown hooks)
    setup_application(app, dp, bot=bot)

    # Add custom startup hook for webhook registration
    async def startup_wrapper(_app: web.Application) -> None:
        await on_startup(bot, config)

    async def shutdown_wrapper(_app: web.Application) -> None:
        await on_shutdown(bot)

    app.on_startup.append(startup_wrapper)
    app.on_shutdown.append(shutdown_wrapper)

    return app


async def main() -> None:
    """
    Main entry point for webhook server.

    Validates configuration, creates bot and dispatcher, and starts server.
    """
    config = get_config()

    # Validate required configuration
    if not config["bot_token"]:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not found in settings or environment variables"
        )

    if not config["webhook_url"]:
        raise ValueError(
            "TELEGRAM_WEBHOOK_URL not found in settings or environment variables. "
            "For local development, use polling mode instead: python manage.py run_telegram_bot"
        )

    if not config["webhook_secret"]:
        logger.warning(
            "TELEGRAM_WEBHOOK_SECRET not set. "
            "This is a security risk in production!"
        )

    # Create bot instance
    bot = Bot(token=config["bot_token"])

    # Create dispatcher with handlers
    dp = create_dispatcher()

    # Create aiohttp application
    app = create_app(bot, dp, config)

    # Log startup info
    logger.info("=" * 60)
    logger.info("MTT Telegram Bot - Webhook Mode")
    logger.info("=" * 60)
    logger.info(f"Webhook URL: {config['webhook_url']}")
    logger.info(f"Listening on: {config['host']}:{config['port']}")
    logger.info(f"Secret token: {'configured' if config['webhook_secret'] else 'NOT SET'}")
    logger.info("=" * 60)

    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, config["host"], config["port"])
    await site.start()

    logger.info(f"Webhook server started on {config['host']}:{config['port']}")

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
