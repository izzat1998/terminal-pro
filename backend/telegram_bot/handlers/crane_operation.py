"""
Handlers for crane operation management via Telegram bot
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async
from django.utils import timezone

from apps.core.services import ActivityLogService
from telegram_bot.keyboards import inline, reply
from telegram_bot.middleware import require_manager_access
from telegram_bot.services.entry_service import BotEntryService
from telegram_bot.states.entry import CraneOperationForm
from telegram_bot.translations import get_text
from telegram_bot.utils import format_container_number


logger = logging.getLogger(__name__)

# Create router for crane operation handlers
crane_operation_router = Router()

# Service instances
entry_service = BotEntryService()
activity_log_service = ActivityLogService()


async def get_user_language(state: FSMContext) -> str:
    """Get user's language from state"""
    data = await state.get_data()
    return data.get("language", "ru")


@crane_operation_router.message(Command("crane"))
@require_manager_access
async def cmd_crane_operation(message: Message, state: FSMContext, user=None):
    """Start crane operation flow"""
    lang = await get_user_language(state)

    await state.clear()
    await state.update_data(language=lang)
    await state.set_state(CraneOperationForm.container_number)

    await message.answer(
        get_text("start_crane_operation", lang),
        reply_markup=reply.get_cancel_keyboard(lang),
    )


@crane_operation_router.message(CraneOperationForm.container_number)
@require_manager_access
async def process_crane_container_number(
    message: Message, state: FSMContext, user=None
):
    """Process container number for crane operation"""
    lang = await get_user_language(state)

    if not message.text:
        await message.answer(
            get_text("error_text_only", lang),
            reply_markup=reply.get_cancel_keyboard(lang),
        )
        return

    raw_input = message.text.strip()

    # Validate format (accepts with or without spaces)
    if not await sync_to_async(entry_service.validate_container_number)(raw_input):
        await message.answer(
            get_text("invalid_container_format", lang),
            reply_markup=reply.get_cancel_keyboard(lang),
        )
        return

    # Normalize: remove spaces and uppercase (e.g., "MSKU 1234567" -> "MSKU1234567")
    container_number = entry_service.normalize_container_number(raw_input)

    # Check if container has active entry (on terminal)
    active_entry = await sync_to_async(entry_service.check_active_entry)(
        container_number
    )

    if not active_entry:
        await message.answer(
            get_text(
                "crane_op_container_not_found", lang, container_number=container_number
            ),
            reply_markup=reply.get_cancel_keyboard(lang),
        )
        return

    # Store entry info and auto-add first crane operation
    entry_id = active_entry.id
    operation_time = timezone.now()

    try:
        # Add crane operation
        operation, total_count = await sync_to_async(entry_service.add_crane_operation)(
            entry_id=entry_id, operation_date=operation_time
        )

        # Log activity
        await sync_to_async(activity_log_service.log_crane_operation_added)(
            user=user,
            telegram_user_id=message.from_user.id,
            crane_operation=operation,
        )

        # Store state data
        await state.update_data(
            container_number=container_number, entry_id=entry_id, operations_added=1
        )
        await state.set_state(CraneOperationForm.adding_operations)

        # Show success message with option to add more
        # Format container number as PREFIX | POSTFIX for better readability
        await message.answer(
            get_text(
                "crane_op_added",
                lang,
                container_number=format_container_number(container_number),
                operation_time=operation_time.strftime("%d.%m.%Y %H:%M"),
                total_count=total_count,
            ),
            reply_markup=inline.get_crane_operation_actions_keyboard(lang),
        )

    except Exception as e:
        logger.error(f"Error adding crane operation: {e!s}", exc_info=True)
        error_msg = str(e)[:100]  # Truncate long errors
        await message.answer(get_text("crane_op_error", lang, error=error_msg))
        # Return to main menu on error
        await state.clear()
        await state.update_data(language=lang)
        await message.answer(
            get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
        )


@crane_operation_router.callback_query(
    F.data == "crane_op_add_more", CraneOperationForm.adding_operations
)
@require_manager_access
async def add_more_crane_operation(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Add another crane operation for the same container"""
    lang = await get_user_language(state)
    data = await state.get_data()

    entry_id = data.get("entry_id")
    container_number = data.get("container_number")
    operations_added = data.get("operations_added", 0)

    operation_time = timezone.now()

    try:
        # Add another crane operation
        operation, total_count = await sync_to_async(entry_service.add_crane_operation)(
            entry_id=entry_id, operation_date=operation_time
        )

        # Log activity
        await sync_to_async(activity_log_service.log_crane_operation_added)(
            user=user,
            telegram_user_id=callback.from_user.id,
            crane_operation=operation,
        )

        # Update count
        operations_added += 1
        await state.update_data(operations_added=operations_added)

        # Update message with new count
        # Format container number as PREFIX | POSTFIX for better readability
        await callback.message.edit_text(
            get_text(
                "crane_op_added",
                lang,
                container_number=format_container_number(container_number),
                operation_time=operation_time.strftime("%d.%m.%Y %H:%M"),
                total_count=total_count,
            ),
            reply_markup=inline.get_crane_operation_actions_keyboard(lang),
        )

    except Exception as e:
        logger.error(f"Error adding crane operation: {e!s}", exc_info=True)
        error_msg = str(e)[:100]
        await callback.message.edit_text(
            get_text("crane_op_error", lang, error=error_msg)
        )
        # Return to main menu on error
        await state.clear()
        await state.update_data(language=lang)
        await callback.message.answer(
            get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
        )

    await callback.answer()


@crane_operation_router.callback_query(
    F.data == "crane_op_done", CraneOperationForm.adding_operations
)
@require_manager_access
async def done_crane_operations(callback: CallbackQuery, state: FSMContext, user=None):
    """Complete crane operations and return to main menu"""
    lang = await get_user_language(state)
    data = await state.get_data()

    container_number = data.get("container_number")
    operations_added = data.get("operations_added", 0)

    # Show completion message
    # Format container number as PREFIX | POSTFIX for better readability
    await callback.message.edit_text(
        get_text(
            "crane_op_completed",
            lang,
            container_number=format_container_number(container_number),
            count=operations_added,
        )
    )

    # Clear state and return to main menu
    await state.clear()
    await state.update_data(language=lang)

    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=reply.get_main_keyboard(lang)
    )

    await callback.answer()
