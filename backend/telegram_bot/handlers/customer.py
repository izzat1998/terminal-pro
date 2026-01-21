"""
Handlers for customer pre-order creation and management.
Multi-plate flow: Enter plates → Operation type for each → Summary → Confirm
"""

import html
import logging
import uuid

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async
from django.db import transaction

from apps.core.services import ActivityLogService
from apps.terminal_operations.services.preorder_service import PreOrderService
from apps.terminal_operations.services.vehicle_entry_service import VehicleEntryService
from telegram_bot.keyboards.customer import (
    get_cancel_order_confirm_keyboard,
    get_customer_cancel_keyboard,
    get_customer_main_keyboard,
    get_operation_type_keyboard,
    get_order_confirmation_keyboard,
    get_order_list_keyboard,
)
from telegram_bot.middleware import require_customer_access
from telegram_bot.states.customer import CustomerOrderManagement, CustomerPreOrderForm
from telegram_bot.translations import get_text


logger = logging.getLogger(__name__)

router = Router()
preorder_service = PreOrderService()
vehicle_entry_service = VehicleEntryService()
activity_log_service = ActivityLogService()

# Valid callback data values for validation
VALID_OPERATION_TYPES = {"LOAD", "UNLOAD"}


async def get_user_language(state: FSMContext) -> str:
    """Get user's language from state"""
    data = await state.get_data()
    return data.get("language", "ru")


def parse_plate_numbers(text: str) -> list:
    """
    Parse multiple plate numbers from text.
    Accepts plates separated by newlines, commas, or spaces.
    Returns list of normalized plate numbers.
    """
    # Split by newlines first
    lines = text.strip().split("\n")
    plates = []

    for line in lines:
        # Also split by comma and space
        parts = line.replace(",", " ").split()
        for part in parts:
            plate = part.strip().upper()
            # Basic validation - at least 3 characters
            if len(plate) >= 3:
                plates.append(plate)

    # Remove duplicates while preserving order
    seen = set()
    unique_plates = []
    for plate in plates:
        if plate not in seen:
            seen.add(plate)
            unique_plates.append(plate)

    return unique_plates


# ============ CREATE ORDER FLOW ============


@router.message(F.text.in_(["📦 Создать заявку", "📦 Buyurtma yaratish"]))
@require_customer_access
async def cmd_create_order(message: Message, state: FSMContext, user=None):
    """Start pre-order creation flow - ask for plate numbers"""
    lang = await get_user_language(state)

    # Clear previous state but keep language
    await state.clear()
    await state.update_data(language=lang)
    await state.set_state(CustomerPreOrderForm.plate_numbers)

    await message.answer(
        get_text("customer_enter_plates", lang),
        reply_markup=get_customer_cancel_keyboard(lang),
        parse_mode="HTML",
    )


@router.message(CustomerPreOrderForm.plate_numbers, F.text)
@require_customer_access
async def process_plate_numbers(message: Message, state: FSMContext, user=None):
    """Process multiple plate numbers"""
    lang = await get_user_language(state)

    # Check for cancel
    if message.text in ["❌ Отменить", "❌ Bekor qilish"]:
        await cancel_order_creation(message, state)
        return

    if not message.text:
        await message.answer(get_text("customer_enter_plates", lang), parse_mode="HTML")
        return

    # Parse plate numbers
    plates = parse_plate_numbers(message.text)

    if not plates:
        await message.answer(
            get_text("customer_plates_invalid", lang), parse_mode="HTML"
        )
        return

    # Store plates and initialize vehicles list
    vehicles = [{"plate": plate, "operation": None} for plate in plates]
    await state.update_data(vehicles=vehicles, current_index=0)

    # Ask operation type for first plate
    await state.set_state(CustomerPreOrderForm.operation_type)
    await ask_operation_for_current_plate(message, state, lang)


async def ask_operation_for_current_plate(
    message_or_callback, state: FSMContext, lang: str, edit: bool = False
):
    """Ask operation type for current plate

    Args:
        message_or_callback: Message or CallbackQuery.message to respond to
        state: FSM context
        lang: User language
        edit: If True, edit the existing message. If False, send a new message.
    """
    data = await state.get_data()
    vehicles = data["vehicles"]
    current_index = data["current_index"]

    current_plate = vehicles[current_index]["plate"]
    total = len(vehicles)

    # Escape plate number for safe HTML display
    safe_plate = html.escape(current_plate)
    text = get_text("customer_ask_operation_for_plate", lang).format(
        index=current_index + 1, total=total, plate=safe_plate
    )

    if edit:
        # Edit existing bot message (used in callback handlers)
        await message_or_callback.edit_text(
            text, reply_markup=get_operation_type_keyboard(lang), parse_mode="HTML"
        )
    else:
        # Send new message (used after user input)
        await message_or_callback.answer(
            text, reply_markup=get_operation_type_keyboard(lang), parse_mode="HTML"
        )


@router.callback_query(
    F.data.startswith("operation_"), CustomerPreOrderForm.operation_type
)
@require_customer_access
async def process_operation_type(callback: CallbackQuery, state: FSMContext, user=None):
    """Process operation type selection for current plate"""
    lang = await get_user_language(state)
    operation_type = callback.data.replace("operation_", "")

    # Validate callback data
    if operation_type not in VALID_OPERATION_TYPES:
        logger.warning(f"Invalid operation type callback data: {callback.data}")
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    data = await state.get_data()
    vehicles = data["vehicles"]
    current_index = data["current_index"]

    # Save operation for current plate
    vehicles[current_index]["operation"] = operation_type

    # Move to next plate or show summary
    next_index = current_index + 1

    if next_index < len(vehicles):
        # More plates to process
        await state.update_data(vehicles=vehicles, current_index=next_index)
        await ask_operation_for_current_plate(callback.message, state, lang, edit=True)
    else:
        # All plates processed - show summary
        await state.update_data(vehicles=vehicles)
        await state.set_state(CustomerPreOrderForm.confirmation)
        await show_summary(callback.message, state, lang)

    await callback.answer()


async def show_summary(message, state: FSMContext, lang: str):
    """Show summary of all vehicles before confirmation"""
    data = await state.get_data()
    vehicles = data["vehicles"]

    # Build summary text
    lines = [f"<b>{get_text('customer_summary_header', lang)}</b>\n"]

    for i, vehicle in enumerate(vehicles, 1):
        operation_text = (
            get_text("operation_load", lang)
            if vehicle["operation"] == "LOAD"
            else get_text("operation_unload", lang)
        )
        # Escape plate number to prevent HTML injection
        safe_plate = html.escape(vehicle["plate"])
        lines.append(f"{i}. <b>{safe_plate}</b> — {operation_text}")

    lines.append(f"\n{get_text('customer_confirm_all', lang)}")

    await message.edit_text(
        "\n".join(lines),
        reply_markup=get_order_confirmation_keyboard(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "order_confirm", CustomerPreOrderForm.confirmation)
@require_customer_access
async def confirm_order(
    callback: CallbackQuery, state: FSMContext, bot: Bot, user=None
):
    """Create all pre-orders after confirmation"""
    lang = await get_user_language(state)
    data = await state.get_data()
    customer = user  # 'user' is the customer injected by middleware
    vehicles = data["vehicles"]

    created_count = 0
    errors = []

    # Generate batch_id to group all orders created together
    batch_id = uuid.uuid4()

    for vehicle in vehicles:
        try:
            # Wrap each vehicle creation in a transaction for atomicity
            @transaction.atomic
            def create_vehicle_with_preorder():
                # Create vehicle entry with WAITING status
                vehicle_entry = vehicle_entry_service.create_vehicle_entry(
                    license_plate=vehicle["plate"],
                    customer=customer,
                    vehicle_type="CARGO",
                )

                # Create pre-order and link to vehicle entry
                # All orders in this batch share the same batch_id
                preorder = preorder_service.create_preorder(
                    customer=customer,
                    plate_number=vehicle["plate"],
                    operation_type=vehicle["operation"],
                    truck_photo=None,  # No photo in new flow
                    batch_id=batch_id,
                )

                # Link PreOrder to VehicleEntry
                preorder.vehicle_entry = vehicle_entry
                preorder.save()

                return preorder

            preorder = await sync_to_async(create_vehicle_with_preorder)()
            created_count += 1

            # Log activity for each created preorder
            await sync_to_async(activity_log_service.log_preorder_created)(
                user=customer,
                telegram_user_id=callback.from_user.id,
                preorder=preorder,
            )

        except Exception as e:
            errors.append(f"{vehicle['plate']}: {e!s}")

    # Show result
    if created_count == len(vehicles):
        await callback.message.edit_text(
            get_text("customer_orders_created", lang).format(count=created_count),
            parse_mode="HTML",
        )
    elif created_count > 0:
        error_text = "\n".join(errors)
        await callback.message.edit_text(
            get_text("customer_orders_partial", lang).format(
                created=created_count, total=len(vehicles), errors=error_text
            ),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            get_text(
                "customer_order_error",
                lang,
                error=errors[0] if errors else "Unknown error",
            )
        )

    # Show main menu
    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=get_customer_main_keyboard(lang)
    )

    # Clear state but keep language
    await state.clear()
    await state.update_data(language=lang)
    await callback.answer()


@router.callback_query(F.data == "order_cancel", CustomerPreOrderForm.confirmation)
@require_customer_access
async def cancel_order_at_confirmation(
    callback: CallbackQuery, state: FSMContext, user=None
):
    """Cancel order at confirmation step"""
    lang = await get_user_language(state)

    await callback.message.edit_text(get_text("operation_cancelled", lang))

    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=get_customer_main_keyboard(lang)
    )

    await state.clear()
    await state.update_data(language=lang)
    await callback.answer()


async def cancel_order_creation(message: Message, state: FSMContext):
    """Cancel order creation at any step"""
    lang = await get_user_language(state)

    await message.answer(
        get_text("operation_cancelled", lang),
        reply_markup=get_customer_main_keyboard(lang),
    )

    await state.clear()
    await state.update_data(language=lang)


# ============ VIEW ORDERS ============


@router.message(F.text.in_(["📋 Мои заявки", "📋 Mening buyurtmalarim"]))
@require_customer_access
async def view_my_orders(message: Message, state: FSMContext, user=None):
    """Show customer's orders"""
    lang = await get_user_language(state)
    customer = user

    orders = await sync_to_async(list)(
        preorder_service.get_customer_orders(customer, limit=10)
    )

    if not orders:
        await message.answer(get_text("customer_no_orders", lang))
        return

    # Format order list
    text = get_text("customer_orders_header", lang)

    for order in orders:
        operation = (
            get_text("operation_load_short", lang)
            if order.operation_type == "LOAD"
            else get_text("operation_unload_short", lang)
        )
        status = get_text(f"order_status_{order.status.lower()}", lang)
        # Escape plate number for safe HTML display
        safe_plate = html.escape(order.plate_number)
        text += get_text(
            "customer_order_item",
            lang,
            id=order.id,
            plate=safe_plate,
            operation=operation,
            status=status,
        )

    await message.answer(text, parse_mode="HTML")


# ============ CANCEL ORDER ============


@router.message(F.text.in_(["❌ Отменить заявку", "❌ Buyurtmani bekor qilish"]))
@require_customer_access
async def start_cancel_order(message: Message, state: FSMContext, user=None):
    """Start order cancellation flow"""
    lang = await get_user_language(state)
    customer = user

    # Get pending orders
    pending_orders = await sync_to_async(list)(
        preorder_service.get_pending_orders(customer)
    )

    if not pending_orders:
        await message.answer(get_text("customer_no_pending_orders", lang))
        return

    await state.set_state(CustomerOrderManagement.viewing_orders)
    await message.answer(
        get_text("customer_select_order_cancel", lang),
        reply_markup=get_order_list_keyboard(pending_orders, lang),
    )


@router.callback_query(
    F.data.startswith("cancel_order_"), CustomerOrderManagement.viewing_orders
)
@require_customer_access
async def select_order_to_cancel(callback: CallbackQuery, state: FSMContext, user=None):
    """Select order to cancel"""
    lang = await get_user_language(state)

    # Safely parse order_id from callback data
    try:
        order_id = int(callback.data.replace("cancel_order_", ""))
    except ValueError:
        logger.warning(f"Invalid order_id in callback data: {callback.data}")
        await callback.answer(get_text("invalid_selection", lang), show_alert=True)
        return

    await state.update_data(cancel_order_id=order_id)
    await state.set_state(CustomerOrderManagement.cancel_confirmation)

    await callback.message.edit_text(
        get_text("customer_confirm_cancel_question", lang),
        reply_markup=get_cancel_order_confirm_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(
    F.data == "cancel_confirm_yes", CustomerOrderManagement.cancel_confirmation
)
@require_customer_access
async def confirm_cancel_order(callback: CallbackQuery, state: FSMContext, user=None):
    """Confirm and cancel order"""
    lang = await get_user_language(state)
    data = await state.get_data()
    customer = user

    try:
        # Cancel order and linked vehicle entry in single sync context
        def cancel_order_with_vehicle(order_id, cust, tg_user_id):
            order = preorder_service.cancel_order(order_id=order_id, customer=cust)
            plate = order.plate_number  # Extract before any lazy loads
            # Also cancel the linked VehicleEntry if it exists and is in WAITING status
            if order.vehicle_entry and order.vehicle_entry.status == "WAITING":
                vehicle_entry_service.cancel(order.vehicle_entry)
            # Log activity in same sync context
            activity_log_service.log_preorder_cancelled(
                user=cust, telegram_user_id=tg_user_id, preorder=order
            )
            return plate

        plate_number = await sync_to_async(cancel_order_with_vehicle)(
            data["cancel_order_id"], customer, callback.from_user.id
        )

        await callback.message.edit_text(
            get_text("customer_order_cancelled", lang, plate=plate_number)
        )
    except Exception as e:
        await callback.message.edit_text(
            get_text("customer_cancel_error", lang, error=str(e))
        )

    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=get_customer_main_keyboard(lang)
    )

    await state.clear()
    await state.update_data(language=lang)
    await callback.answer()


@router.callback_query(
    F.data == "cancel_confirm_no", CustomerOrderManagement.cancel_confirmation
)
@require_customer_access
async def decline_cancel_order(callback: CallbackQuery, state: FSMContext, user=None):
    """User decided not to cancel"""
    lang = await get_user_language(state)

    await callback.message.edit_text(get_text("operation_cancelled", lang))

    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=get_customer_main_keyboard(lang)
    )

    await state.clear()
    await state.update_data(language=lang)
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
@require_customer_access
async def back_to_menu(callback: CallbackQuery, state: FSMContext, user=None):
    """Go back to main menu"""
    lang = await get_user_language(state)

    await callback.message.edit_text(get_text("operation_cancelled", lang))

    await callback.message.answer(
        get_text("choose_action", lang), reply_markup=get_customer_main_keyboard(lang)
    )

    await state.clear()
    await state.update_data(language=lang)
    await callback.answer()


# ============ HELP ============


@router.message(F.text.in_(["ℹ️ Справка", "ℹ️ Ma'lumot"]))
@require_customer_access
async def customer_help(message: Message, state: FSMContext, user=None):
    """Show customer help - only for customers"""
    lang = await get_user_language(state)

    await message.answer(
        get_text("customer_help", lang), reply_markup=get_customer_main_keyboard(lang)
    )
