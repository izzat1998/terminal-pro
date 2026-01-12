"""
Main bot application
"""
# ruff: noqa: E402  # Imports must come after django.setup()

import asyncio
import logging
import os
import sys

import django


# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terminal_app.settings")
django.setup()

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from telegram_bot.handlers import (
    common,
    container_cabinet,
    crane_operation,
    customer,
    entry,
    exit,
    manager_access,
)
from telegram_bot.middleware import ManagerAccessMiddleware


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the bot"""

    # Get bot token from Django settings or environment
    from django.conf import settings

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or os.getenv(
        "TELEGRAM_BOT_TOKEN"
    )
    if not bot_token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not found in settings or environment variables"
        )

    # Initialize Bot instance
    bot = Bot(token=bot_token)

    # Setup storage (Redis if available, Memory otherwise)
    try:
        from redis.asyncio import Redis

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "1"))

        redis = Redis(host=redis_host, port=redis_port, db=redis_db)
        await redis.ping()
        storage = RedisStorage(redis)
        logger.info("Using Redis storage for FSM")
    except Exception as e:
        logger.warning(f"Redis not available, using Memory storage: {e}")
        storage = MemoryStorage()

    # Initialize Dispatcher
    dp = Dispatcher(storage=storage)

    # Register middleware to inject manager into all handlers
    dp.message.middleware(ManagerAccessMiddleware())
    dp.callback_query.middleware(ManagerAccessMiddleware())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECURITY: Router registration order is CRITICAL for role isolation!
    # ═══════════════════════════════════════════════════════════════════════════
    # aiogram processes handlers in registration order - first match wins.
    #
    # Order explanation:
    # 1. manager_access - Phone verification for new users (unregistered)
    # 2. customer - Customer-only handlers with @require_customer_access decorator
    #    MUST be before common to intercept shared button text (Help, Cancel)
    # 3. common - Shared handlers for managers (after customer handlers skip)
    # 4+ - Manager-specific routers with @require_manager_access decorator
    #
    # WARNING: DO NOT REORDER without security review!
    # Changing order could allow role bypass or break button handling.
    # ═══════════════════════════════════════════════════════════════════════════
    dp.include_router(manager_access.router)
    dp.include_router(customer.router)  # MUST be before common.router
    dp.include_router(container_cabinet.router)  # Customer container cabinet
    dp.include_router(common.router)
    dp.include_router(entry.router)
    dp.include_router(exit.exit_router)
    dp.include_router(crane_operation.crane_operation_router)

    logger.info("Bot started successfully!")

    # Start polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
