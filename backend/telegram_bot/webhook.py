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

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from django.conf import settings

from telegram_bot.handlers import (
    common,
    container_cabinet,
    customer,
    entry,
    exit,
    manager_access,
)
from telegram_bot.health import health_check, readiness_check
from telegram_bot.middleware import ManagerAccessMiddleware


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

        redis = Redis(host=redis_host, port=redis_port, db=redis_db)
        storage = RedisStorage(redis)
        logger.info(f"Using Redis storage: {redis_host}:{redis_port}/{redis_db}")
    except Exception as e:
        logger.warning(f"Redis not available, using Memory storage: {e}")
        storage = MemoryStorage()

    # Create dispatcher
    dp = Dispatcher(storage=storage)

    # Register middleware
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

    logger.info("Dispatcher configured with all handlers")
    return dp


def create_app(bot: Bot, dp: Dispatcher, config: dict) -> web.Application:
    """
    Create the aiohttp web application.

    Sets up webhook handler, health checks, and lifecycle hooks.
    """
    app = web.Application()

    # Create webhook request handler with secret token verification
    webhook_handler = SimpleRequestHandler(
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
