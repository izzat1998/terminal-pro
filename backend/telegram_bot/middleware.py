"""
Middleware and decorators for Telegram bot access control.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from asgiref.sync import sync_to_async

from apps.accounts.services import ManagerService


logger = logging.getLogger(__name__)


class UpdateDeduplicationMiddleware(BaseMiddleware):
    """
    Middleware to prevent duplicate processing of the same Telegram message.

    Deduplicates based on message content (chat_id + message_id) rather than
    update_id, because Telegram can send the same message with different update_ids
    when the user has multiple clients or network issues cause retransmission.

    Uses asyncio.Lock for thread-safe check-and-set operations since multiple
    requests can arrive concurrently.
    """

    # Class-level cache shared across all instances
    # Key: dedup_key (str), Value: timestamp
    _seen_messages: dict[str, float] = {}
    _cleanup_interval = 60  # seconds
    _last_cleanup = 0.0
    _max_age = 300  # Keep entries for 5 minutes
    _lock: asyncio.Lock | None = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """Get or create the asyncio lock (must be created in async context)."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    def _get_dedup_key(self, update: Update) -> str | None:
        """
        Generate a deduplication key based on message content.

        For messages: chat_id:message_id
        For callbacks: callback_query_id (globally unique)
        For edited messages: chat_id:message_id:edited
        """
        if update.message:
            return f"msg:{update.message.chat.id}:{update.message.message_id}"
        elif update.callback_query:
            # callback_query.id is globally unique
            return f"cb:{update.callback_query.id}"
        elif update.edited_message:
            # Include "edited" to distinguish from original message
            return f"edited:{update.edited_message.chat.id}:{update.edited_message.message_id}"
        return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Check if this message has already been processed.
        Uses lock to ensure atomic check-and-set for concurrent requests.
        """
        update: Update | None = None
        if isinstance(event, Update):
            update = event
        else:
            update = data.get("event_update")

        if not update:
            return await handler(event, data)

        dedup_key = self._get_dedup_key(update)

        if not dedup_key:
            # Update type we can't deduplicate, process normally
            return await handler(event, data)

        current_time = time.time()
        lock = self._get_lock()

        async with lock:
            # Periodic cleanup of old entries
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._cleanup_old_entries(current_time)
                UpdateDeduplicationMiddleware._last_cleanup = current_time

            # Check if we've seen this message
            if dedup_key in self._seen_messages:
                logger.debug(f"Skipping duplicate message: {dedup_key}")
                return None  # Skip duplicate

            # Mark as seen BEFORE releasing lock
            UpdateDeduplicationMiddleware._seen_messages[dedup_key] = current_time

        # Process the update
        return await handler(event, data)

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Remove entries older than max_age."""
        cutoff = current_time - self._max_age
        old_keys = [
            key for key, ts in self._seen_messages.items()
            if ts < cutoff
        ]
        for key in old_keys:
            del UpdateDeduplicationMiddleware._seen_messages[key]
        if old_keys:
            logger.debug(f"Cleaned up {len(old_keys)} old dedup entries")


def _get_user_bot_access_sync(user) -> bool:
    """
    Synchronous version - Get bot_access from profile first, fall back to legacy field.
    Works for both managers and customers.
    """
    profile = user.get_profile()
    if profile and hasattr(profile, 'bot_access'):
        return profile.bot_access
    return user.bot_access


def _get_user_telegram_linked_sync(user) -> bool:
    """
    Synchronous version - Check if telegram is linked via profile first, fall back to legacy field.
    """
    profile = user.get_profile()
    if profile:
        return profile.telegram_user_id is not None
    return user.telegram_user_id is not None


async def get_user_bot_access(user) -> bool:
    """
    Get bot_access from profile first, fall back to legacy field.
    Works for both managers and customers.
    Async-safe wrapper for use in aiogram handlers.
    """
    return await sync_to_async(_get_user_bot_access_sync)(user)


async def get_user_telegram_linked(user) -> bool:
    """
    Check if telegram is linked via profile first, fall back to legacy field.
    Async-safe wrapper for use in aiogram handlers.
    """
    return await sync_to_async(_get_user_telegram_linked_sync)(user)


class ManagerAccessMiddleware(BaseMiddleware):
    """
    Middleware to check if user has manager access to the bot.
    Automatically injects manager object into handler data if access is granted.
    """

    def __init__(self):
        self.service = ManagerService()
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Check manager access before processing the handler.
        """
        # Get user from event
        user = None
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return await handler(event, data)

        telegram_user_id = user.id

        # Try to get user (admin or manager) by telegram_user_id (wrap in sync_to_async)
        manager = await sync_to_async(self.service.get_user_by_telegram_id)(
            telegram_user_id
        )

        # Inject user into data for handlers to use
        data["user"] = manager
        data["telegram_user_id"] = telegram_user_id
        data["telegram_username"] = user.username or ""

        # Continue to handler
        return await handler(event, data)


def require_manager_access(handler: Callable) -> Callable:
    """
    Decorator to require manager access for a handler.
    If user doesn't have access, shows appropriate message and blocks handler.
    IMPORTANT: This decorator blocks customers - use require_customer_access for customer handlers.

    Usage:
        @router.message(Command("some_command"))
        @require_manager_access
        async def handler(message: Message, state: FSMContext, user):
            # handler code here - user is injected by middleware
            pass
    """

    @functools.wraps(handler)
    async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
        # Get user from kwargs (injected by middleware)
        user = kwargs.get("user")
        telegram_user_id = kwargs.get("telegram_user_id")

        # Get state if available
        state: FSMContext = kwargs.get("state")

        # Get language from state
        lang = "ru"  # default
        if state:
            data = await state.get_data()
            lang = data.get("language", "ru")

        # Import translations
        from telegram_bot.translations import get_text

        # If no user found, they need to register
        if not user:
            logger.warning(
                f"Access denied: Telegram user {telegram_user_id} not registered"
            )

            message = event if isinstance(event, Message) else event.message
            if not message:
                logger.error(
                    f"Cannot send reply: original message was deleted for user {telegram_user_id}"
                )
                return

            await message.answer(get_text("not_registered", lang), parse_mode="HTML")
            return

        # Block customers from manager handlers - they should use customer handlers
        if user.user_type == "customer":
            logger.debug(
                f"Customer {user.full_name} tried to access manager handler - skipping"
            )
            return  # Silent skip - let customer handlers pick it up

        # Note: is_active controls website access only, not bot access
        # Bot access is controlled by bot_access flag

        # Check if user has bot access (profile first, then legacy)
        if not await get_user_bot_access(user):
            logger.warning(f"Access denied: User {user.full_name} has no bot access")

            message = event if isinstance(event, Message) else event.message
            if not message:
                logger.error(
                    f"Cannot send reply: original message was deleted for user {user.id}"
                )
                return

            await message.answer(get_text("access_denied", lang), parse_mode="HTML")
            return

        # Check if telegram is linked (profile first, then legacy)
        if not await get_user_telegram_linked(user):
            logger.error(
                f"Unexpected state: User {user.full_name} found but telegram not linked"
            )

            message = event if isinstance(event, Message) else event.message
            if not message:
                logger.error(
                    f"Cannot send reply: original message was deleted for user {user.id}"
                )
                return

            await message.answer(
                get_text("telegram_not_linked", lang), parse_mode="HTML"
            )
            return

        # User has access, call the handler
        logger.info(
            f"Access granted to {user.user_type}: {user.full_name} (ID: {user.id})"
        )
        return await handler(event, *args, **kwargs)

    return wrapper


def require_customer_access(handler: Callable) -> Callable:
    """
    Decorator to require customer access for a handler.
    Only allows users with user_type='customer' and bot_access=True.

    Usage:
        @router.message(F.text.in_(['📦 Создать заявку']))
        @require_customer_access
        async def handler(message: Message, state: FSMContext, user):
            # handler code here - user (customer) is injected by middleware
            pass
    """

    @functools.wraps(handler)
    async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
        # Get user (customer) from kwargs (injected by middleware)
        user = kwargs.get("user")
        telegram_user_id = kwargs.get("telegram_user_id")

        # Get state if available
        state: FSMContext = kwargs.get("state")

        # Get language from state
        lang = "ru"  # default
        if state:
            data = await state.get_data()
            lang = data.get("language", "ru")

        # Import translations
        from telegram_bot.translations import get_text

        # If no user found, they need to register
        if not user:
            logger.warning(
                f"Customer access denied: Telegram user {telegram_user_id} not registered"
            )
            message = event if isinstance(event, Message) else event.message
            if message:
                await message.answer(
                    get_text("not_registered", lang), parse_mode="HTML"
                )
            return

        # Only allow customers
        if user.user_type != "customer":
            logger.debug(
                f"Non-customer {user.full_name} tried to access customer handler - skipping"
            )
            return  # Silent skip - let other handlers pick it up

        # Note: is_active controls website access only, not bot access
        # Bot access is controlled by bot_access flag

        # Check if customer has bot access (profile first, then legacy)
        if not await get_user_bot_access(user):
            logger.warning(
                f"Customer access denied: {user.full_name} has no bot access"
            )
            message = event if isinstance(event, Message) else event.message
            if message:
                await message.answer(
                    get_text("customer_access_denied", lang), parse_mode="HTML"
                )
            return

        # Customer has access, call the handler
        logger.info(f"Customer access granted: {user.full_name} (ID: {user.id})")
        return await handler(event, *args, **kwargs)

    return wrapper


def optional_user_access(handler: Callable) -> Callable:
    """
    Decorator that injects user if available, but doesn't block if not.
    Useful for handlers that work both with and without user (like /start).

    Usage:
        @router.message(Command("start"))
        @optional_user_access
        async def handler(message: Message, state: FSMContext, user=None):
            # Handler code here - user can be None if not registered
            pass
    """

    @functools.wraps(handler)
    async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
        # User is already injected by middleware
        # Just call the handler
        return await handler(event, *args, **kwargs)

    return wrapper
