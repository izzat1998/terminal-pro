"""
Handlers for manager phone verification and access control
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Contact, Message
from asgiref.sync import sync_to_async

from apps.accounts.models import CustomUser
from apps.accounts.services import ManagerService
from apps.core.exceptions import BusinessLogicError
from telegram_bot.keyboards.customer import get_customer_main_keyboard
from telegram_bot.keyboards.inline import get_phone_share_keyboard
from telegram_bot.keyboards.reply import get_main_keyboard
from telegram_bot.middleware import get_user_bot_access
from telegram_bot.states.entry import PhoneVerification
from telegram_bot.translations import get_text


logger = logging.getLogger(__name__)
router = Router()


def mask_phone(phone: str) -> str:
    """Mask phone number for logging - show only last 4 digits"""
    if not phone or len(phone) < 4:
        return "****"
    return "*" * (len(phone) - 4) + phone[-4:]


async def check_manager_access(telegram_user_id: int) -> tuple[CustomUser | None, str]:
    """
    Check if telegram user (admin or manager) has bot access.

    Returns:
        tuple: (CustomUser instance or None, status code)
        Status codes:
            - 'has_access': User exists, is active, and has bot_access
            - 'needs_phone': User not found, needs phone verification
            - 'no_access': User exists but no bot_access
            - 'pending_request': User has pending access request
            - 'deactivated': User exists but is deactivated
    """
    service = ManagerService()

    # Wrap database call in sync_to_async - now works for all user types
    user = await sync_to_async(service.get_user_by_telegram_id)(telegram_user_id)

    if not user:
        return None, "needs_phone"

    if not user.is_active:
        return user, "deactivated"

    # Check bot_access from profile first, then legacy field
    if not await get_user_bot_access(user):
        return user, "no_access"

    return user, "has_access"


async def request_phone_verification(
    message: Message, state: FSMContext, lang: str = "ru"
):
    """
    Request phone number from user for verification.
    """
    await state.set_state(PhoneVerification.waiting_for_phone)
    await message.answer(
        get_text("phone_share_request", lang),
        reply_markup=get_phone_share_keyboard(lang),
        parse_mode="HTML",
    )


@router.message(PhoneVerification.waiting_for_phone, F.contact)
async def handle_phone_contact(message: Message, state: FSMContext):
    """
    Handle phone number shared via contact button.
    """
    contact: Contact = message.contact
    phone_number = contact.phone_number
    telegram_user_id = message.from_user.id
    telegram_username = message.from_user.username or ""

    # Get language from state
    data = await state.get_data()
    lang = data.get("language", "ru")

    # Ensure phone starts with +
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number

    logger.info(
        f"Phone verification attempt: {mask_phone(phone_number)} for telegram user {telegram_user_id}"
    )

    service = ManagerService()

    try:
        # Try to activate telegram user with this phone (wrap in sync_to_async)
        manager, status = await sync_to_async(service.activate_telegram_user)(
            phone_number=phone_number,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
        )

        # Clear phone verification state and store user_type for keyboard selection
        user_type = manager.user_type
        await state.clear()
        await state.update_data(language=lang, manager_id=manager.id, user_type=user_type)

        # Check if user has access
        if status["has_access"] and status["can_use_bot"]:
            # Success! User has access - select keyboard based on user_type
            if user_type == "customer":
                keyboard = get_customer_main_keyboard(lang)
                welcome_key = "customer_welcome"
            else:
                keyboard = get_main_keyboard(lang)
                welcome_key = "phone_verification_success"

            await message.answer(
                get_text(welcome_key, lang),
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            logger.info(
                f"Phone verified successfully for {user_type} {manager.first_name} (ID: {manager.id})"
            )

        elif not status["has_access"]:
            # Manager exists but no access
            await message.answer(get_text("access_denied", lang), parse_mode="HTML")
            logger.info(
                f"Phone verified but no access for manager {manager.first_name} (ID: {manager.id})"
            )

    except BusinessLogicError as e:
        logger.warning(f"Phone verification failed: {e.message}")

        # Build restart hint
        restart_hint = "\n\n" + get_text("restart_hint", lang)

        if e.error_code == "PHONE_NOT_REGISTERED":
            await message.answer(
                get_text("phone_not_registered", lang, phone_number=phone_number) + restart_hint,
                parse_mode="HTML",
            )
        elif e.error_code == "MANAGER_DEACTIVATED":
            await message.answer(
                get_text("phone_account_deactivated", lang, phone_number=phone_number) + restart_hint,
                parse_mode="HTML",
            )
        elif e.error_code == "TELEGRAM_ALREADY_LINKED":
            await message.answer(
                get_text("telegram_already_linked", lang) + restart_hint,
                parse_mode="HTML",
            )
        else:
            await message.answer(
                get_text("generic_error", lang, error=e.message) + restart_hint,
                parse_mode="HTML",
            )

        # Clear state
        await state.clear()
        await state.update_data(language=lang)


@router.message(PhoneVerification.waiting_for_phone)
async def handle_non_contact_message(message: Message, state: FSMContext):
    """
    Handle non-contact messages during phone verification.
    Supports both Russian and Uzbek languages.
    """
    data = await state.get_data()
    lang = data.get("language", "ru")

    await message.answer(
        get_text("phone_verification_instruction", lang),
        reply_markup=get_phone_share_keyboard(lang),
    )


# Access request workflow removed - managers get access directly from admin
