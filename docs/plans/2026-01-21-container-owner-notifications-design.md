# Container Owner Telegram Notifications

**Date:** 2026-01-21
**Status:** Approved

## Overview

Send Telegram notifications to container owner groups when a container entry is created via the Telegram bot.

## Requirements

- **Target:** Container owner's Telegram group receives notifications
- **Content:** Full details (container number, ISO type, status, transport type, transport number, entry time, manager name, photos)
- **Trigger:** Only from Telegram bot entry creation (not API/Excel import)
- **Error handling:** Silent fail (log error, entry succeeds)
- **Configuration:** Both Django admin and Vue frontend
- **Language:** Russian

## Design

### 1. Model Changes

Add Telegram notification fields to `ContainerOwner` model:

```python
# apps/terminal_operations/models.py

class ContainerOwner(TimestampedModel):
    name = models.CharField(max_length=250, unique=True, ...)
    slug = models.SlugField(max_length=250, unique=True, ...)

    # Telegram notification settings
    telegram_group_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Telegram группа",
        help_text="ID группы (-1001234567890) или username (@mygroup)",
    )
    telegram_group_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Название группы",
    )
    notifications_enabled = models.BooleanField(
        default=False,
        verbose_name="Уведомления включены",
    )
```

### 2. Notification Service

Create dedicated service for sending container owner notifications:

```python
# telegram_bot/services/owner_notification_service.py

class OwnerNotificationService:
    """Send notifications to container owner Telegram groups"""

    async def notify_container_entry(
        self,
        bot: Bot,
        entry: ContainerEntry,
        manager: CustomUser,
        photo_file_ids: list[str] | None = None
    ) -> bool:
        """
        Send entry notification to container owner's group.
        Returns True if sent, False if skipped/failed (silent).
        """
```

**Message format:**
```
📦 Новый контейнер на терминале

📋 Контейнер: MSKU 1234567
📐 ISO тип: 45G1
📊 Статус: Гружёный
🚛 Транспорт: Авто (01A777BC)
🕐 Время въезда: 21.01.2026 14:35
👤 Менеджер: Иван Петров

+ Photos attached if available
```

### 3. Integration Point

Call notification service from entry handler after successful creation:

```python
# telegram_bot/handlers/entry.py - in confirm_entry()

# After entry is created successfully:
entry = await sync_to_async(entry_service.create_entry)(...)

# Send notification to container owner's group
notification_service = OwnerNotificationService()
await notification_service.notify_container_entry(
    bot=bot,
    entry=entry,
    manager=user,
    photo_file_ids=all_photo_file_ids,
)
```

### 4. API Changes

Extend ContainerOwner serializer:

```python
# apps/terminal_operations/serializers/containers.py

class ContainerOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContainerOwner
        fields = [
            'id', 'name', 'slug',
            'telegram_group_id',
            'telegram_group_name',
            'notifications_enabled',
        ]
```

### 5. Frontend Changes

Add Telegram settings fields to ContainerOwner edit UI:

```vue
<a-form-item label="Telegram группа">
  <a-input v-model:value="form.telegram_group_id"
           placeholder="-1001234567890 или @groupname" />
</a-form-item>

<a-form-item label="Название группы">
  <a-input v-model:value="form.telegram_group_name" />
</a-form-item>

<a-form-item label="Уведомления">
  <a-switch v-model:checked="form.notifications_enabled" />
</a-form-item>
```

## Implementation Order

1. Model + Migration
2. Notification Service
3. Handler Integration
4. API Serializer update
5. Vue Frontend update
6. Test end-to-end

## Files to Modify/Create

| File | Action |
|------|--------|
| `backend/apps/terminal_operations/models.py` | Modify - add fields |
| `backend/apps/terminal_operations/migrations/` | Create - new migration |
| `backend/telegram_bot/services/owner_notification_service.py` | Create |
| `backend/telegram_bot/handlers/entry.py` | Modify - add notification call |
| `backend/apps/terminal_operations/serializers/` | Modify - add fields |
| `frontend/src/views/ContainerOwners.vue` | Modify - add form fields |
