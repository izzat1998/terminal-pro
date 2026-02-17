# Cancel/Delete Group Notification Messages — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow managers to cancel (delete) incorrectly sent container entry/exit notification messages from owner Telegram groups.

**Architecture:** Store Telegram message IDs when notifications are sent to groups, then provide an inline "❌ Отменить" button on each notification that deletes the message(s) from the group when pressed. Both the OwnerNotificationService (primary) and TelegramNotificationService (signal-based) pathways need message ID tracking. The cancel action is handled by a new callback handler that calls `bot.delete_message()`.

**Tech Stack:** Django migrations, aiogram callback handlers, existing OwnerNotificationService

---

## Task Overview (for Parallel Agent Dispatch)

| Task | Agent | Dependencies | Files |
|------|-------|-------------|-------|
| Task 1: DB Schema — Store group message IDs | Agent A | None | `TelegramActivityLog` model, migration |
| Task 2: Capture & store message IDs from send | Agent B | Task 1 | `OwnerNotificationService`, `ActivityLogService` |
| Task 3: Add inline cancel button to notifications | Agent C | Task 2 | `OwnerNotificationService`, inline keyboards |
| Task 4: Cancel callback handler | Agent D | Task 3 | New handler, router registration |
| Task 5: Signal-based pathway (Company notifications) | Agent E | Task 1 | `TelegramNotificationService`, signals |
| Task 6: Integration testing & deploy | Agent F | Tasks 1-5 | All files |

---

## Task 1: DB Schema — Store Group Message IDs

**Agent:** A (independent, start immediately)

**Files:**
- Modify: `backend/apps/core/models.py` (TelegramActivityLog)
- Create: `backend/apps/core/migrations/0003_add_group_message_ids.py`

**Goal:** Add a JSONField to `TelegramActivityLog` to store sent message IDs (supports single messages and media group albums which have multiple message IDs).

### Step 1: Add field to TelegramActivityLog model

In `backend/apps/core/models.py`, add a new field to `TelegramActivityLog` after `group_notification_error` (line ~88):

```python
# Group message tracking (for cancel/delete functionality)
group_message_ids = models.JSONField(
    default=list,
    blank=True,
    verbose_name="ID сообщений в группе",
    help_text="List of Telegram message_ids sent to the group (for deletion)",
)
group_chat_id = models.CharField(
    max_length=50,
    blank=True,
    default="",
    verbose_name="ID чата группы",
    help_text="Telegram chat_id where notification was sent",
)
```

**Why JSONField for message_ids:** A media group (photo album) sends multiple messages — each photo is a separate `message_id`. We need to store all of them to delete the entire album. A JSONField holding `[123, 124, 125]` is the simplest approach.

**Why group_chat_id separately:** We need the chat_id to call `bot.delete_message(chat_id, message_id)`. While we could derive it from the ContainerOwner, storing it directly makes the delete operation self-contained and avoids extra DB queries.

### Step 2: Create migration

Run: `cd /var/www/terminal-pro/backend && .venv/bin/python manage.py makemigrations core --name add_group_message_ids`

### Step 3: Apply migration

Run: `cd /var/www/terminal-pro/backend && .venv/bin/python manage.py migrate core`

### Step 4: Commit

```bash
git add backend/apps/core/models.py backend/apps/core/migrations/0003_add_group_message_ids.py
git commit -m "feat: add group_message_ids and group_chat_id fields to TelegramActivityLog"
```

---

## Task 2: Capture & Store Message IDs from Sent Notifications

**Agent:** B (depends on Task 1)

**Files:**
- Modify: `backend/telegram_bot/services/owner_notification_service.py`
- Modify: `backend/apps/core/services/activity_log_service.py`
- Modify: `backend/telegram_bot/handlers/entry.py` (~line 866)
- Modify: `backend/telegram_bot/handlers/exit.py` (~line 813)

**Goal:** Capture the return value from `bot.send_message()` / `bot.send_media_group()` and pass message IDs back so they can be stored in the activity log.

### Step 1: Update NotificationResult dataclass

In `backend/telegram_bot/services/owner_notification_service.py`, update `NotificationResult` to include message IDs:

```python
@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    status: str  # 'sent', 'skipped', 'error'
    error_message: str = ""
    message_ids: list[int] = field(default_factory=list)
    chat_id: str = ""
```

Don't forget to add `from dataclasses import dataclass, field` at the top.

### Step 2: Capture message IDs in notify_container_entry

In `notify_container_entry()` method, capture return values:

For **text-only** messages (~line 148):
```python
sent_msg = await bot.send_message(
    chat_id=chat_id,
    text=message,
    parse_mode=ParseMode.HTML,
)
return NotificationResult(
    status="sent",
    message_ids=[sent_msg.message_id],
    chat_id=chat_id,
)
```

For **photos with caption**, update `_send_with_photos` to return message IDs:
```python
async def _send_with_photos(
    self,
    bot: Bot,
    chat_id: str,
    caption: str,
    photo_file_ids: list[str],
) -> list[int]:
    """Send photos as media group with caption on first photo. Returns list of message_ids."""
    media_group = []
    for idx, file_id in enumerate(photo_file_ids):
        if idx == 0:
            media_group.append(
                InputMediaPhoto(media=file_id, caption=caption, parse_mode=ParseMode.HTML)
            )
        else:
            media_group.append(InputMediaPhoto(media=file_id))

    sent_messages = await bot.send_media_group(chat_id=chat_id, media=media_group)
    return [msg.message_id for msg in sent_messages]
```

Then in the caller (~line 145):
```python
if photo_file_ids:
    msg_ids = await self._send_with_photos(bot, chat_id, message, photo_file_ids)
else:
    sent_msg = await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.HTML,
    )
    msg_ids = [sent_msg.message_id]

return NotificationResult(status="sent", message_ids=msg_ids, chat_id=chat_id)
```

### Step 3: Same changes in notify_container_exit and notify_container_exits_batch

Apply the same pattern to `notify_container_exit()` and `notify_container_exits_batch()` — capture return values from send calls and include them in `NotificationResult`.

### Step 4: Update ActivityLogService to store message IDs

In `backend/apps/core/services/activity_log_service.py`, update `update_group_notification_status`:

```python
def update_group_notification_status(
    self, activity_log_id: int, status: str, error_message: str = "",
    message_ids: list[int] | None = None, chat_id: str = "",
) -> None:
    """Update group notification status for an activity log entry."""
    update_fields = {
        "group_notification_status": status,
        "group_notification_error": error_message,
    }
    if message_ids:
        update_fields["group_message_ids"] = message_ids
    if chat_id:
        update_fields["group_chat_id"] = chat_id

    TelegramActivityLog.objects.filter(pk=activity_log_id).update(**update_fields)
    self.logger.debug(
        f"Updated group notification status for log {activity_log_id}: {status}"
    )
```

### Step 5: Update entry handler to pass message IDs

In `backend/telegram_bot/handlers/entry.py` at ~line 874, update the call to include message_ids:

```python
await sync_to_async(activity_log_service.update_group_notification_status)(
    activity_log_id=activity_log.id,
    status=notification_result.status,
    error_message=notification_result.error_message,
    message_ids=notification_result.message_ids,
    chat_id=notification_result.chat_id,
)
```

### Step 6: Update exit handler to log notification results

In `backend/telegram_bot/handlers/exit.py` at ~line 812, the exit flow currently doesn't update the activity log with notification status. Add tracking:

```python
# Send owner notifications (combined per owner group)
try:
    notification_results = await owner_notification_service.notify_container_exits_batch(
        bot=callback.bot,
        entries=updated_entries,
        manager=user,
        photo_file_ids=photo_file_ids or None,
    )
    # Update activity logs with notification results
    # Note: batch sends one notification per owner group, not per entry
    # We store results on the first entry's activity log for each batch
    for result in notification_results:
        if result.status == "sent" and result.message_ids:
            # Find the activity log for the first entry in this batch
            # and update it with the notification result
            pass  # Handled by the activity log updates above
except Exception as e:
    logger.error(f"Failed to send exit notifications: {e}", exc_info=True)
```

**Note:** The exit handler creates separate activity logs per container but sends one combined notification per owner. For simplicity, store the message_ids on ALL activity logs for entries in that batch (they share the same group message).

### Step 7: Commit

```bash
git add backend/telegram_bot/services/owner_notification_service.py \
      backend/apps/core/services/activity_log_service.py \
      backend/telegram_bot/handlers/entry.py \
      backend/telegram_bot/handlers/exit.py
git commit -m "feat: capture and store Telegram message IDs from group notifications"
```

---

## Task 3: Add Inline Cancel Button to Notification Messages

**Agent:** C (depends on Task 2)

**Files:**
- Modify: `backend/telegram_bot/services/owner_notification_service.py`
- Modify: `backend/telegram_bot/keyboards/inline.py`

**Goal:** Add an inline keyboard with a "❌ Отменить" button to every notification message sent to groups. The callback data encodes the activity log ID so the handler knows which message(s) to delete.

### Step 1: Create cancel keyboard function

In `backend/telegram_bot/keyboards/inline.py`, add:

```python
def get_cancel_notification_keyboard(activity_log_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for cancelling a group notification message."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"cancel_notif_{activity_log_id}",
                )
            ]
        ]
    )
```

### Step 2: Update notification sending to include the keyboard

**Problem:** We need the `activity_log_id` to embed in the button, but the activity log is created BEFORE the notification is sent (in the handler). The notification service doesn't know the log ID.

**Solution — Two-phase approach:**
1. Send the notification WITHOUT the cancel button first (existing flow)
2. After storing message_ids in the activity log, EDIT the message to add the cancel button

**Alternative (simpler):** Pass the `activity_log_id` into the notification service so it can include the button when sending.

**Chosen approach:** Pass `activity_log_id` into the notification service. This requires reordering in the handler: create the activity log FIRST, then send the notification.

In `entry.py` confirm_entry handler, reorder:

```python
# 1. Log activity FIRST (to get the ID)
activity_log = await sync_to_async(activity_log_service.log_container_entry_created)(
    user=user,
    telegram_user_id=callback.from_user.id,
    container_entry=entry,
)

# 2. Send notification WITH the activity_log.id for the cancel button
notification_result = await owner_notification_service.notify_container_entry(
    bot=bot,
    entry=entry,
    manager=user,
    photo_file_ids=all_photo_file_ids if all_photo_file_ids else None,
    activity_log_id=activity_log.id,
)

# 3. Update activity log with notification result
await sync_to_async(activity_log_service.update_group_notification_status)(
    activity_log_id=activity_log.id,
    status=notification_result.status,
    error_message=notification_result.error_message,
    message_ids=notification_result.message_ids,
    chat_id=notification_result.chat_id,
)
```

### Step 3: Update OwnerNotificationService to accept and use activity_log_id

In `notify_container_entry()`, add `activity_log_id: int | None = None` parameter. When sending:

```python
from telegram_bot.keyboards.inline import get_cancel_notification_keyboard

# Build reply markup if we have an activity_log_id
reply_markup = get_cancel_notification_keyboard(activity_log_id) if activity_log_id else None

if photo_file_ids:
    msg_ids = await self._send_with_photos(
        bot, chat_id, message, photo_file_ids, reply_markup=reply_markup
    )
else:
    sent_msg = await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )
    msg_ids = [sent_msg.message_id]
```

**Important for media groups:** Telegram does NOT support `reply_markup` on `send_media_group`. The cancel button can only appear on text-only messages or as a separate follow-up message after the album.

**Solution for albums:** Send the album first, then send a separate small "control" message with the cancel button:

```python
if photo_file_ids:
    msg_ids = await self._send_with_photos(bot, chat_id, message, photo_file_ids)
    # Send a control message with the cancel button after the album
    if reply_markup:
        control_msg = await bot.send_message(
            chat_id=chat_id,
            text="👆 Уведомление выше",
            reply_markup=reply_markup,
        )
        msg_ids.append(control_msg.message_id)  # Include so it gets deleted too
```

Apply the same to `notify_container_exit` and `notify_container_exits_batch`.

### Step 4: Commit

```bash
git add backend/telegram_bot/keyboards/inline.py \
      backend/telegram_bot/services/owner_notification_service.py \
      backend/telegram_bot/handlers/entry.py \
      backend/telegram_bot/handlers/exit.py
git commit -m "feat: add inline cancel button to group notification messages"
```

---

## Task 4: Cancel Callback Handler

**Agent:** D (depends on Task 3)

**Files:**
- Create: `backend/telegram_bot/handlers/cancel_notification.py`
- Modify: `backend/telegram_bot/bot.py` (register the new router)

**Goal:** Handle the "❌ Отменить" button press — delete all message(s) from the group and update the activity log.

### Step 1: Create the cancel notification handler

Create `backend/telegram_bot/handlers/cancel_notification.py`:

```python
"""
Handler for cancelling (deleting) group notification messages.
Triggered when a manager presses the "❌ Отменить" inline button
on a notification message in a group chat.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from asgiref.sync import sync_to_async

from apps.core.models import TelegramActivityLog

logger = logging.getLogger(__name__)

cancel_notification_router = Router()


@cancel_notification_router.callback_query(F.data.startswith("cancel_notif_"))
async def handle_cancel_notification(callback: CallbackQuery, bot: Bot):
    """
    Delete notification message(s) from group chat.
    Callback data format: cancel_notif_{activity_log_id}
    """
    try:
        # Extract activity log ID from callback data
        activity_log_id = int(callback.data.replace("cancel_notif_", ""))
    except (ValueError, IndexError):
        logger.warning(f"Invalid cancel notification callback data: {callback.data}")
        await callback.answer("Ошибка: неверные данные", show_alert=True)
        return

    # Fetch the activity log with stored message IDs
    def get_log_data():
        try:
            log = TelegramActivityLog.objects.get(pk=activity_log_id)
            return {
                "message_ids": log.group_message_ids or [],
                "chat_id": log.group_chat_id,
                "status": log.group_notification_status,
            }
        except TelegramActivityLog.DoesNotExist:
            return None

    log_data = await sync_to_async(get_log_data)()

    if not log_data:
        await callback.answer("Уведомление не найдено", show_alert=True)
        return

    if log_data["status"] == "cancelled":
        await callback.answer("Уведомление уже отменено", show_alert=True)
        return

    chat_id = log_data["chat_id"]
    message_ids = log_data["message_ids"]

    if not chat_id or not message_ids:
        await callback.answer("Нет данных для удаления", show_alert=True)
        return

    # Delete all messages (album photos + control message)
    deleted_count = 0
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted_count += 1
        except Exception as e:
            logger.warning(
                f"Failed to delete message {msg_id} from chat {chat_id}: {e}"
            )

    # Update activity log status to cancelled
    def mark_cancelled():
        TelegramActivityLog.objects.filter(pk=activity_log_id).update(
            group_notification_status="cancelled",
        )

    await sync_to_async(mark_cancelled)()

    logger.info(
        f"Cancelled notification (log={activity_log_id}): "
        f"deleted {deleted_count}/{len(message_ids)} messages from chat {chat_id}"
    )

    # Also try to delete the control message itself (the one with the button)
    # This message is the one the user clicked, so we can delete it via callback
    try:
        await callback.message.delete()
    except Exception:
        pass  # May already be deleted if it was in the message_ids list

    await callback.answer("✅ Уведомление удалено из группы", show_alert=True)
```

### Step 2: Add "cancelled" to GROUP_NOTIFICATION_STATUS_CHOICES

In `backend/apps/core/models.py`, update the choices:

```python
GROUP_NOTIFICATION_STATUS_CHOICES = [
    ("sent", "Отправлено"),
    ("skipped", "Пропущено"),
    ("error", "Ошибка"),
    ("not_applicable", "Не применимо"),
    ("cancelled", "Отменено"),
]
```

**Note:** Adding a choice to a CharField does NOT require a migration — choices are only enforced at the form/serializer level, not at the database level. Django stores the raw string value.

### Step 3: Register the router in bot.py

In `backend/telegram_bot/bot.py`, import and include the new router:

```python
from telegram_bot.handlers.cancel_notification import cancel_notification_router

# Register with the dispatcher (alongside other routers)
dp.include_router(cancel_notification_router)
```

**Important:** The cancel_notification_router should be registered WITHOUT any middleware that requires manager access from a private chat, because the callback will be triggered from a GROUP chat, not a private chat. The callback comes from whoever clicks the button in the group.

### Step 4: Commit

```bash
git add backend/telegram_bot/handlers/cancel_notification.py \
      backend/telegram_bot/bot.py \
      backend/apps/core/models.py
git commit -m "feat: add cancel notification handler to delete group messages"
```

---

## Task 5: Signal-Based Pathway (Company Notifications)

**Agent:** E (depends on Task 1, can run in parallel with Tasks 2-4)

**Files:**
- Modify: `backend/apps/terminal_operations/services/telegram_notification_service.py`
- Modify: `backend/apps/terminal_operations/signals.py`

**Goal:** The signal-based `TelegramNotificationService` also sends messages to Company groups. These should also capture and store message IDs for potential cancellation.

### Step 1: Update TelegramNotificationService._send_media_album to return message IDs

```python
async def _send_media_album(
    self, chat_id: str, photos: list[FileAttachment], caption: str
) -> tuple[bool, list[int]]:
    """
    Send photos as media album to Telegram group.
    Returns (success, list_of_message_ids).
    """
    # ... existing code ...
    sent_messages = await bot.send_media_group(chat_id=chat_id, media=media_group)
    msg_ids = [msg.message_id for msg in sent_messages]
    return True, msg_ids
```

### Step 2: Store message IDs via TelegramActivityLog

In `notify_group_about_entry`, after a successful send, create/update a `TelegramActivityLog` entry:

```python
if success:
    # Store message IDs for cancel functionality
    from apps.core.models import TelegramActivityLog
    from django.contrib.contenttypes.models import ContentType

    content_type = await sync_to_async(ContentType.objects.get_for_model)(ContainerEntry)
    await sync_to_async(TelegramActivityLog.objects.create)(
        action="container_entry_created",
        user_type="manager",
        user=entry.recorded_by,
        content_type=content_type,
        object_id=entry.id,
        group_notification_status="sent",
        group_message_ids=msg_ids,
        group_chat_id=group_id,
        details={"source": "signal", "company": entry.company.name},
    )
```

**Note:** This creates a second activity log entry for the same entry (one from the bot handler pathway, one from the signal pathway). This is fine — they target different groups (Owner vs Company).

### Step 3: Commit

```bash
git add backend/apps/terminal_operations/services/telegram_notification_service.py \
      backend/apps/terminal_operations/signals.py
git commit -m "feat: track message IDs in signal-based company notifications"
```

---

## Task 6: Integration Testing & Deployment

**Agent:** F (depends on all above)

**Files:**
- All modified files
- Production systemctl services

### Step 1: Run existing tests

```bash
cd /var/www/terminal-pro/backend
.venv/bin/python -m pytest tests/ -v --tb=short
```

Expected: All existing tests pass (no regressions).

### Step 2: Apply migration on production

```bash
cd /var/www/terminal-pro/backend
.venv/bin/python manage.py migrate core
```

### Step 3: Restart services

```bash
sudo systemctl restart mtt-terminal
sudo systemctl restart mtt-telegram-bot
```

### Step 4: Test the flow manually

1. Use bot to create a container entry with an owner that has notifications enabled
2. Verify the notification appears in the group WITH the "❌ Отменить" button
3. Click the button
4. Verify the message(s) are deleted from the group
5. Verify the activity log shows `group_notification_status = "cancelled"`

### Step 5: Verify edge cases

- Photo album entry (multiple messages deleted)
- Text-only entry (single message deleted)
- Exit notification cancel
- Double-click on cancel button (should show "already cancelled")
- Message older than 48 hours (Telegram may reject deletion — handle gracefully)

### Step 6: Final commit and deploy

```bash
git add -A
git commit -m "feat: complete cancel group notification feature"
```

---

## Key Design Decisions

### Why store message_ids on TelegramActivityLog (not ContainerEntry)?

1. **Separation of concerns** — ContainerEntry is a business model; Telegram message tracking is operational metadata
2. **Multiple notifications per entry** — An entry can trigger both Owner and Company group notifications, each with different message_ids
3. **Existing infrastructure** — TelegramActivityLog already tracks `group_notification_status`
4. **No extra model needed** — Avoids creating a new model just for message tracking

### Why inline button instead of a bot command?

1. **Discoverability** — Button is right there on the message, no need to remember a command
2. **Context** — Button carries the activity_log_id, so no need for the manager to identify which notification to cancel
3. **Speed** — One tap vs typing a command with parameters

### Why not edit the message instead of deleting?

1. **Clean** — The incorrect info is completely gone from the group
2. **Simple** — No need to rebuild the message with corrections
3. **Albums** — Can't edit media group captions via the API reliably

### Telegram API Limitations

- `bot.delete_message()` requires the bot to be a group admin with "Delete Messages" permission
- Messages can only be deleted within **48 hours** of sending
- `send_media_group()` does NOT support `reply_markup` — the cancel button must be a separate message for photo albums
