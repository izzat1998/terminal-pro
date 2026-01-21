"""
Middleware and decorators for Telegram bot access control.
"""

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from asgiref.sync import sync_to_async

from apps.accounts.services import ManagerService


logger = logging.getLogger(__name__)


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
