# Keyboards package
from .customer import (
    get_cancel_order_confirm_keyboard,
    get_customer_cancel_keyboard,
    get_customer_main_keyboard,
    get_operation_type_keyboard,
    get_order_confirmation_keyboard,
    get_order_list_keyboard,
    get_plate_confirmation_keyboard,
)
from .reply import get_cancel_keyboard, get_main_keyboard, remove_keyboard


__all__ = [
    # Reply keyboards
    "get_main_keyboard",
    "get_cancel_keyboard",
    "remove_keyboard",
    # Customer keyboards
    "get_customer_main_keyboard",
    "get_customer_cancel_keyboard",
    "get_operation_type_keyboard",
    "get_plate_confirmation_keyboard",
    "get_order_confirmation_keyboard",
    "get_order_list_keyboard",
    "get_cancel_order_confirm_keyboard",
]
