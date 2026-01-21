# Group Notification Tracking Design

**Date:** 2026-01-21
**Status:** Approved

## Overview

Track whether Telegram group notifications were sent successfully when a container entry is created. Display this status in the Activity table on the `/telegram-bot` page.

## Requirements

- Log group notification result (sent/skipped/error) for each container entry
- Show reason when notification was skipped or failed
- Display in frontend Activity table with appropriate visual indicators

## Data Model

Add two fields to `TelegramActivityLog` model:

```python
GROUP_NOTIFICATION_STATUS_CHOICES = [
    ('sent', 'Отправлено'),
    ('skipped', 'Пропущено'),
    ('error', 'Ошибка'),
    ('not_applicable', 'Не применимо'),
]

group_notification_status = CharField(
    max_length=20,
    choices=GROUP_NOTIFICATION_STATUS_CHOICES,
    default='not_applicable'
)
group_notification_error = TextField(blank=True, default='')
```

## Service Layer

### NotificationResult dataclass

```python
@dataclass
class NotificationResult:
    status: str  # 'sent', 'skipped', 'error'
    error_message: str = ''
```

### OwnerNotificationService changes

`notify_container_entry()` returns `NotificationResult` instead of `bool`:

| Scenario | Status | Error Message |
|----------|--------|---------------|
| Successfully sent | `sent` | (empty) |
| No owner configured | `skipped` | "Владелец не указан" |
| Notifications disabled | `skipped` | "Уведомления отключены" |
| No group ID | `skipped` | "Группа не настроена" |
| Telegram API error | `error` | Exception message |

### ActivityLogService changes

New method:

```python
def update_group_notification_status(
    self,
    activity_log_id: int,
    status: str,
    error_message: str = ''
) -> None
```

### Entry handler flow

1. Create entry
2. Log activity → returns `TelegramActivityLog` instance
3. Send notification → returns `NotificationResult`
4. Update activity log with notification result

## Frontend

### New column

Position: After "Статус", before "Дата"

```typescript
{ title: 'Группа', key: 'groupNotification', width: 120, align: 'center' }
```

### Display

| Status | Display |
|--------|---------|
| `sent` | Green tag: "✓ Отправлено" |
| `skipped` | Gray tag with tooltip: "⏭ Пропущено" |
| `error` | Red tag with tooltip: "✗ Ошибка" |
| `not_applicable` | Muted dash: "—" |

### Type updates

```typescript
interface TelegramActivityLog {
  // ... existing fields
  group_notification_status: 'sent' | 'skipped' | 'error' | 'not_applicable';
  group_notification_error: string;
}
```

## Files to Modify

### Backend
1. `apps/core/models.py` - Add fields to TelegramActivityLog
2. `apps/core/migrations/` - New migration
3. `telegram_bot/services/owner_notification_service.py` - Return NotificationResult
4. `apps/core/services/activity_log_service.py` - Add update method, return log instance
5. `apps/core/serializers.py` - Add new fields to serializer
6. `telegram_bot/handlers/entry.py` - Capture and store notification result

### Frontend
1. `frontend/src/services/telegramActivityService.ts` - Update types
2. `frontend/src/views/TelegramBotSettings.vue` - Add column and display logic
