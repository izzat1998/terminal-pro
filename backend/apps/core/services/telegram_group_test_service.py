"""
Service for testing Telegram group accessibility.
"""

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNotFound
from django.conf import settings


logger = logging.getLogger(__name__)


@dataclass
class GroupTestResult:
    """Result of testing group access."""
    accessible: bool
    group_title: str | None = None
    group_type: str | None = None
    member_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None


class TelegramGroupTestService:
    """Test Telegram group accessibility for the bot."""

    def __init__(self):
        self.bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)

    async def _test_group_async(self, group_id: str) -> GroupTestResult:
        """
        Async implementation of group test.
        Uses bot.get_chat() to verify access and fetch group info.
        """
        if not self.bot_token:
            return GroupTestResult(
                accessible=False,
                error_code="BOT_NOT_CONFIGURED",
                error_message="Telegram бот не настроен",
            )

        # Validate group_id format
        group_id = group_id.strip()
        if not group_id:
            return GroupTestResult(
                accessible=False,
                error_code="INVALID_ID",
                error_message="ID группы не указан",
            )

        bot = Bot(token=self.bot_token)

        try:
            chat = await bot.get_chat(chat_id=group_id)

            # Check if it's a group/supergroup/channel (not private chat)
            if chat.type not in ("group", "supergroup", "channel"):
                return GroupTestResult(
                    accessible=False,
                    error_code="NOT_A_GROUP",
                    error_message="Указанный ID не является группой или каналом",
                )

            # member_count requires separate API call in aiogram 3.x, skip it
            return GroupTestResult(
                accessible=True,
                group_title=chat.title,
                group_type=chat.type,
                member_count=None,
            )

        except TelegramNotFound:
            return GroupTestResult(
                accessible=False,
                error_code="GROUP_NOT_FOUND",
                error_message="Группа не найдена или недоступна",
            )

        except TelegramForbiddenError:
            return GroupTestResult(
                accessible=False,
                error_code="BOT_KICKED",
                error_message="Бот был удалён из группы",
            )

        except TelegramBadRequest as e:
            error_text = str(e).lower()

            if "chat not found" in error_text:
                return GroupTestResult(
                    accessible=False,
                    error_code="GROUP_NOT_FOUND",
                    error_message="Группа не найдена или недоступна",
                )

            if "bot is not a member" in error_text:
                return GroupTestResult(
                    accessible=False,
                    error_code="BOT_NOT_MEMBER",
                    error_message="Бот не является участником группы",
                )

            if "invalid" in error_text:
                return GroupTestResult(
                    accessible=False,
                    error_code="INVALID_ID",
                    error_message="Неверный формат ID группы",
                )

            logger.error(f"Telegram API error testing group {group_id}: {e}")
            return GroupTestResult(
                accessible=False,
                error_code="TELEGRAM_ERROR",
                error_message=f"Ошибка Telegram API: {e}",
            )

        except Exception as e:
            logger.exception(f"Unexpected error testing group {group_id}: {e}")
            return GroupTestResult(
                accessible=False,
                error_code="UNKNOWN_ERROR",
                error_message="Неизвестная ошибка при проверке группы",
            )

        finally:
            await bot.session.close()

    def test_group(self, group_id: str) -> GroupTestResult:
        """
        Sync wrapper for testing group access.
        Can be called from Django views.
        """
        return asyncio.run(self._test_group_async(group_id))
