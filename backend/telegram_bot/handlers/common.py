import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.customer import get_customer_main_keyboard
from telegram_bot.keyboards.inline import get_language_keyboard
from telegram_bot.keyboards.reply import get_main_keyboard
from telegram_bot.middleware import require_manager_access
from telegram_bot.states.entry import LanguageSelection
from telegram_bot.translations import get_text


logger = logging.getLogger(__name__)
router = Router()


async def get_user_language(state: FSMContext) -> str:
    """Get user's selected language from state, default to Russian"""
    data = await state.get_data()
    return data.get("language", "ru")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle /start command.
    First checks if user has manager access.
    New users select language BEFORE phone verification.
    Existing users see language selection or welcome if already registered.
    """
    telegram_user_id = message.from_user.id

    # Import here to avoid circular dependency
    from telegram_bot.handlers.manager_access import check_manager_access

    # Check if manager exists and has access
    manager, status = await check_manager_access(telegram_user_id)

    # Get language from state or default
    data = await state.get_data()
    lang = data.get("language", "ru")

    if status == "has_access":
        # User has full access - show language selection or welcome
        user_type = manager.user_type if manager else "manager"
        logger.info(
            f"{user_type.capitalize()} {manager.full_name} (ID: {manager.id}) started bot with access"
        )
        await state.update_data(manager_id=manager.id, user_type=user_type)

        # If no language selected yet, show language selection
        if not lang or lang == "ru":
            await state.set_state(LanguageSelection.choosing)
            await message.answer(
                get_text("choose_language", "ru"), reply_markup=get_language_keyboard()
            )
        else:
            # Already has language, show welcome based on user type
            if user_type == "customer":
                await message.answer(
                    get_text("customer_welcome", lang),
                    reply_markup=get_customer_main_keyboard(lang),
                )
            else:
                await message.answer(
                    get_text("welcome", lang), reply_markup=get_main_keyboard(lang)
                )

    elif status == "needs_phone":
        # New user - show language selection FIRST, then phone verification
        # (Phone verification will happen after language selection callback)
        logger.info(
            f"New telegram user {telegram_user_id} - showing language selection first"
        )
        await state.set_state(LanguageSelection.choosing)
        await message.answer(
            get_text("choose_language", "ru"), reply_markup=get_language_keyboard()
        )
        # Mark this state as "new_user_registration" by storing a flag
        await state.update_data(awaiting_phone_verification=True)

    elif status == "deactivated":
        # Manager deactivated
        logger.warning(f"Deactivated manager {manager.full_name} tried to access bot")
        await message.answer(get_text("account_deactivated", lang), parse_mode="HTML")

    elif status == "pending_request":
        # Manager has pending request
        logger.info(f"Manager {manager.full_name} with pending request started bot")
        await state.update_data(manager_id=manager.id)
        await message.answer(
            get_text("access_request_pending", lang), parse_mode="HTML"
        )

    elif status == "no_access":
        # Manager exists but no access
        logger.info(f"Manager {manager.full_name} without access started bot")
        await state.update_data(manager_id=manager.id)
        from telegram_bot.keyboards.inline import get_request_access_keyboard

        await message.answer(
            get_text("access_denied", lang),
            reply_markup=get_request_access_keyboard(lang),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("lang_"), LanguageSelection.choosing)
async def language_selected(callback: CallbackQuery, state: FSMContext, user=None):
    """
    Handle language selection.
    - For existing users: show welcome screen
    - For new users: proceed to phone verification
    """
    lang = callback.data.replace("lang_", "")

    # Get state data to check if new user awaiting phone verification
    data = await state.get_data()
    awaiting_phone = data.get("awaiting_phone_verification", False)

    # Update state with selected language
    await state.update_data(language=lang)

    if awaiting_phone:
        # New user - proceed to phone verification after language selection
        logger.info(
            f"New user selected language: {lang}, proceeding to phone verification"
        )

        # Clear the flag
        await state.update_data(awaiting_phone_verification=False)

        # Set phone verification state
        from telegram_bot.states.entry import PhoneVerification

        await state.set_state(PhoneVerification.waiting_for_phone)

        # Send phone share keyboard in a new message (replacing language selection)
        from telegram_bot.keyboards.inline import get_phone_share_keyboard

        await callback.message.answer(
            get_text("phone_share_request", lang),
            reply_markup=get_phone_share_keyboard(lang),
            parse_mode="HTML",
        )
    else:
        # Existing user with access - show welcome screen based on user type
        # Get user_type from database (via middleware) first, then state, then default
        if user:
            user_type = user.user_type
        else:
            user_type = data.get("user_type", "manager")

        await state.clear()  # Clear language selection state
        await state.update_data(
            language=lang, user_type=user_type
        )  # Preserve language and user_type

        # Show welcome message based on user type
        if user_type == "customer":
            await callback.message.edit_text(get_text("customer_welcome", lang))
            await callback.message.answer(
                get_text("choose_action", lang),
                reply_markup=get_customer_main_keyboard(lang),
            )
        else:
            await callback.message.edit_text(get_text("welcome", lang))
            await callback.message.answer(
                get_text("choose_action", lang), reply_markup=get_main_keyboard(lang)
            )

    await callback.answer()


@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext):
    """Handle /language command - change language"""
    await state.set_state(LanguageSelection.choosing)
    await message.answer(
        get_text("choose_language", "ru"), reply_markup=get_language_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    """Handle /help command"""
    lang = await get_user_language(state)
    await message.answer(get_text("help_text", lang))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, user=None):
    """Handle /cancel command"""
    await handle_cancel(message, state, user)


async def handle_cancel(message: Message, state: FSMContext, user=None):
    """Common cancel logic for both command and button"""
    lang = await get_user_language(state)
    current_state = await state.get_state()
    data = await state.get_data()

    # Get user_type from database (via middleware) first, then state, then default
    if user:
        user_type = user.user_type
    else:
        user_type = data.get("user_type", "manager")

    # Choose correct keyboard based on user type
    if user_type == "customer":
        keyboard = get_customer_main_keyboard(lang)
    else:
        keyboard = get_main_keyboard(lang)

    if current_state is None:
        await message.answer(get_text("no_operation", lang), reply_markup=keyboard)
        return

    # Clean up any pending tasks for this user
    user_id = message.from_user.id
    # Import here to avoid circular import
    from telegram_bot.handlers.entry import cancel_photo_confirmation_task

    cancel_photo_confirmation_task(user_id)

    # Preserve language and user_type when clearing state
    current_lang = lang
    await state.clear()
    await state.update_data(language=current_lang, user_type=user_type)

    await message.answer(get_text("operation_cancelled", lang), reply_markup=keyboard)


# Button text handlers
@router.message(
    F.text.in_(
        [
            "🚛 Въезд",  # Russian
            "🚛 Kirish",  # Uzbek
        ]
    )
)
@require_manager_access
async def btn_create_entry(message: Message, state: FSMContext, user=None):
    """Handle 'Create Entry' button click"""
    # Import here to avoid circular import
    from telegram_bot.handlers.entry import cmd_create_entry

    await cmd_create_entry(message, state, user=user)


@router.message(
    F.text.in_(
        [
            "ℹ️ Справка",  # Russian
            "ℹ️ Ma'lumot",  # Uzbek
        ]
    )
)
async def btn_help(message: Message, state: FSMContext):
    """Handle 'Help' button click"""
    await cmd_help(message, state)


@router.message(
    F.text.in_(
        [
            "🌍 Язык",  # Russian
            "🌍 Til",  # Uzbek
        ]
    )
)
async def btn_change_language(message: Message, state: FSMContext):
    """Handle 'Change Language' button click"""
    await cmd_language(message, state)


@router.message(
    F.text.in_(
        [
            "❌ Отменить",  # Russian
            "❌ Bekor qilish",  # Uzbek
        ]
    )
)
async def btn_cancel(message: Message, state: FSMContext, user=None):
    """Handle 'Cancel' button click"""
    await handle_cancel(message, state, user)


@router.message(
    F.text.in_(
        [
            "🚚 Выезд",  # Russian
            "🚚 Chiqish",  # Uzbek
        ]
    )
)
@require_manager_access
async def btn_exit_container(message: Message, state: FSMContext, user=None):
    """Handle 'Exit Container' button click"""
    # Import here to avoid circular import
    from telegram_bot.handlers.exit import cmd_exit_container

    await cmd_exit_container(message, state, user=user)


@router.message(
    F.text.in_(
        [
            "🏗️ Кран",  # Russian
            "🏗️ Kran",  # Uzbek
        ]
    )
)
@require_manager_access
async def btn_crane_operation(message: Message, state: FSMContext, user=None):
    """Handle 'Crane Operation' button click"""
    # Import here to avoid circular import
    from telegram_bot.handlers.crane_operation import cmd_crane_operation

    await cmd_crane_operation(message, state, user=user)


# ═══════════════════════════════════════════════════════════════════════════
# Fallback router for stale inline buttons (FSM state lost)
# MUST be registered LAST in bot.py to catch unhandled callbacks
# ═══════════════════════════════════════════════════════════════════════════
fallback_router = Router()


@fallback_router.callback_query()
async def fallback_callback_handler(callback: CallbackQuery, state: FSMContext):
    """
    Catch-all handler for callback queries that weren't handled by any other router.
    This happens when a user's FSM state is lost but they click old inline buttons.

    Clears stale data and prompts user to restart with /start.
    """
    logger.warning(
        f"Unhandled callback from user {callback.from_user.id}: {callback.data} "
        f"(state lost or expired)"
    )

    # Get language from data if available, default to Russian
    data = await state.get_data()
    lang = data.get("language", "ru")

    # Clear all stale FSM data
    await state.clear()

    # Answer the callback to stop loading indicator
    await callback.answer()

    # Send message asking user to restart
    restart_message = {
        "ru": "⚠️ Сессия устарела. Пожалуйста, нажмите /start чтобы начать заново.",
        "uz": "⚠️ Sessiya eskirgan. Iltimos, /start bosing va qaytadan boshlang.",
    }

    await callback.message.answer(restart_message.get(lang, restart_message["ru"]))
