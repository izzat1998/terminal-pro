from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from telegram_bot.translations import get_text


def get_main_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Main keyboard shown when no active operation.
    Shows: Create Entry, Exit Container, Crane Operation, Help, Language
    """
    builder = ReplyKeyboardBuilder()

    # Row 1: Create Entry, Exit Container, Crane Operation
    builder.button(text=get_text("btn_create_entry", lang))
    builder.button(text=get_text("btn_exit_container", lang))
    builder.button(text=get_text("btn_crane_operation", lang))

    # Row 2: Help, Language
    builder.button(text=get_text("btn_help", lang))
    builder.button(text=get_text("btn_change_language", lang))

    builder.adjust(3, 2)  # 3 buttons in first row, 2 in second

    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Keyboard shown during entry creation.
    Shows: Cancel, Help
    """
    builder = ReplyKeyboardBuilder()

    builder.button(text=get_text("btn_cancel_operation", lang))
    builder.button(text=get_text("btn_help", lang))

    builder.adjust(2)  # 2 buttons in one row

    return builder.as_markup(resize_keyboard=True)


def remove_keyboard():
    """Remove keyboard (used when showing inline keyboards)"""
    from aiogram.types import ReplyKeyboardRemove

    return ReplyKeyboardRemove()
