# Telegram Group Access Test Feature

## Overview

Add ability to test whether the Telegram bot has access to a group before saving it on ContainerOwner (and Companies). Prevents configuration errors where notifications silently fail.

## Decisions

| Question | Decision |
|----------|----------|
| When to test? | Both on-demand button AND automatic on save |
| Save behavior on failure? | Block if `notifications_enabled=true`, warn but allow if disabled |
| Feedback level? | Detailed info + auto-fill group name from Telegram |
| Endpoint location? | Dedicated `/api/telegram/test-group/` (reusable) |

## API Design

### Endpoint

`POST /api/telegram/test-group/`

**Request:**
```json
{
  "group_id": "-1001234567890"
}
```

**Success response:**
```json
{
  "success": true,
  "data": {
    "accessible": true,
    "group_title": "Owner Notifications",
    "group_type": "supergroup",
    "member_count": 15
  }
}
```

**Failure response:**
```json
{
  "success": false,
  "data": {
    "accessible": false,
    "error_code": "BOT_NOT_MEMBER",
    "error_message": "Бот не является участником группы"
  }
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| `BOT_NOT_MEMBER` | Bot isn't in the group |
| `GROUP_NOT_FOUND` | Group doesn't exist or is private |
| `INVALID_ID` | Malformed group ID |
| `BOT_KICKED` | Bot was removed from group |
| `NO_SEND_PERMISSION` | Bot can't send messages (restricted) |

## Backend Implementation

### New App Structure

```
apps/telegram/
├── __init__.py
├── urls.py                       # Routes /api/telegram/*
├── views.py                      # TestGroupView
└── services/
    └── group_test_service.py     # TelegramGroupTestService
```

### Service

```python
class TelegramGroupTestService:
    """Test Telegram group accessibility for the bot."""

    async def test_group_access(self, group_id: str) -> dict:
        """
        Test if bot can access and send to a Telegram group.

        Uses bot.get_chat() to verify access and fetch group info.
        Returns dict with accessible, group_title, group_type, member_count
        or error_code and error_message on failure.
        """
```

### URL Configuration

Add to `terminal_app/urls.py`:
```python
path("api/telegram/", include("apps.telegram.urls")),
```

## Frontend Implementation

### UI Changes (ContainerOwners.vue)

Add to both create and edit modals:

1. **Test button** next to group_id input field
2. **Status indicator** below the field showing test result
3. **Auto-fill** group_name field on successful test

```
┌─────────────────────────────────────────────────┐
│ ID группы                                       │
│ ┌─────────────────────────────────┐ ┌────────┐ │
│ │ -1001234567890                  │ │ Тест 🔍│ │
│ └─────────────────────────────────┘ └────────┘ │
│                                                 │
│ ✓ Бот имеет доступ к группе                    │
│   Тип: supergroup, 15 участников               │
│                                                 │
│ Название группы                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ Owner Notifications (auto-filled)           │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### New Service

`frontend/src/services/telegramService.ts`:
```typescript
export const telegramService = {
  async testGroup(groupId: string): Promise<GroupTestResult> {
    return http.post('/telegram/test-group/', { group_id: groupId });
  }
};
```

### Save Validation Flow

```
User clicks "Сохранить"
         │
         ▼
   Has group_id?
    │         │
   No        Yes
    │         │
    ▼         ▼
  Save    Test group API
 directly      │
          ┌────┴────┐
          │         │
       Success    Failed
          │         │
          ▼         ▼
        Save    notifications_enabled?
                  │         │
                 Yes        No
                  │         │
                  ▼         ▼
               Block     Show warning modal
               save      "Сохранить всё равно?"
               with           │
               error     ┌────┴────┐
                        Да       Нет
                         │         │
                         ▼         ▼
                       Save     Cancel
```

### Error Messages

- **Block (notifications ON):** "Невозможно сохранить: бот не имеет доступа к группе. Добавьте бота в группу или отключите уведомления."
- **Warning (notifications OFF):** "Бот не имеет доступа к группе. Уведомления не будут отправляться. Сохранить всё равно?"

## Files to Create/Modify

### Backend (New)
- `apps/telegram/__init__.py`
- `apps/telegram/urls.py`
- `apps/telegram/views.py`
- `apps/telegram/services/__init__.py`
- `apps/telegram/services/group_test_service.py`

### Backend (Modify)
- `terminal_app/urls.py` - add telegram app routes
- `terminal_app/settings.py` - add 'apps.telegram' to INSTALLED_APPS

### Frontend (New)
- `src/services/telegramService.ts`

### Frontend (Modify)
- `src/views/ContainerOwners.vue` - add test button and validation

## Future Reuse

This endpoint can be used by:
- `ContainerOwners.vue` (this feature)
- `Companies.vue` (same telegram notification fields)
- Any future feature needing telegram group validation

## Testing

- Unit test: `TelegramGroupTestService` with mocked bot responses
- API test: endpoint returns correct responses for various scenarios
- Frontend: manual testing of button, auto-fill, and save validation
