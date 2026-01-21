# Telegram Group Access Test - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add API endpoint and frontend UI to test if the Telegram bot has access to a group before saving ContainerOwner configurations.

**Architecture:** New service in `apps/core/services/` using aiogram Bot to call `get_chat()`. View added to existing `apps/core/views.py`. Frontend adds test button and validation to ContainerOwners.vue modal forms.

**Tech Stack:** Django REST Framework, aiogram 3.x, Vue 3 Composition API, Ant Design Vue

---

### Task 1: Backend Service - TelegramGroupTestService

**Files:**
- Create: `apps/core/services/telegram_group_test_service.py`

**Step 1: Create the service file**

```python
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

            return GroupTestResult(
                accessible=True,
                group_title=chat.title,
                group_type=chat.type,
                member_count=chat.member_count,
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
```

**Step 2: Run linting to verify syntax**

Run: `cd /var/www/terminal-pro/backend && python -m py_compile apps/core/services/telegram_group_test_service.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add apps/core/services/telegram_group_test_service.py
git commit -m "feat(telegram): add TelegramGroupTestService for group access testing"
```

---

### Task 2: Backend API View

**Files:**
- Modify: `apps/core/views.py`
- Modify: `apps/core/urls.py`

**Step 1: Add view to apps/core/views.py**

Add these imports at the top:
```python
from rest_framework.views import APIView
from apps.core.services.telegram_group_test_service import TelegramGroupTestService
```

Add view class at the end of file:
```python
class TestTelegramGroupView(APIView):
    """
    Test if the Telegram bot has access to a group.

    POST /api/telegram/test-group/
    {
        "group_id": "-1001234567890"  // or "@groupname"
    }

    Returns group info on success, error details on failure.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        group_id = request.data.get("group_id", "").strip()

        if not group_id:
            return Response(
                {
                    "success": False,
                    "data": {
                        "accessible": False,
                        "error_code": "INVALID_ID",
                        "error_message": "ID группы не указан",
                    },
                },
                status=400,
            )

        service = TelegramGroupTestService()
        result = service.test_group(group_id)

        if result.accessible:
            return Response(
                {
                    "success": True,
                    "data": {
                        "accessible": True,
                        "group_title": result.group_title,
                        "group_type": result.group_type,
                        "member_count": result.member_count,
                    },
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "data": {
                        "accessible": False,
                        "error_code": result.error_code,
                        "error_message": result.error_message,
                    },
                }
            )
```

**Step 2: Add URL route to apps/core/urls.py**

Update the file to:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TelegramActivityLogViewSet, TestTelegramGroupView


router = DefaultRouter()
router.register(r"activity-logs", TelegramActivityLogViewSet, basename="activity-log")

urlpatterns = [
    path("", include(router.urls)),
    path("test-group/", TestTelegramGroupView.as_view(), name="test-telegram-group"),
]
```

**Step 3: Test endpoint manually**

Run: `cd /var/www/terminal-pro/backend && source .venv/bin/activate && python manage.py check`
Expected: System check identified no issues.

**Step 4: Commit**

```bash
git add apps/core/views.py apps/core/urls.py
git commit -m "feat(telegram): add test-group API endpoint"
```

---

### Task 3: Backend Unit Tests

**Files:**
- Create: `tests/core/test_telegram_group_test_service.py`

**Step 1: Create test file**

```python
"""
Tests for TelegramGroupTestService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNotFound

from apps.core.services.telegram_group_test_service import (
    GroupTestResult,
    TelegramGroupTestService,
)


class TestTelegramGroupTestService:
    """Tests for TelegramGroupTestService."""

    @pytest.fixture
    def service(self):
        """Create service instance with mocked bot token."""
        with patch.object(TelegramGroupTestService, "__init__", lambda self: None):
            svc = TelegramGroupTestService()
            svc.bot_token = "test-token"
            return svc

    def test_empty_group_id_returns_invalid_id(self, service):
        """Test that empty group_id returns INVALID_ID error."""
        result = service.test_group("")
        assert result.accessible is False
        assert result.error_code == "INVALID_ID"

    def test_whitespace_group_id_returns_invalid_id(self, service):
        """Test that whitespace-only group_id returns INVALID_ID error."""
        result = service.test_group("   ")
        assert result.accessible is False
        assert result.error_code == "INVALID_ID"

    @patch("apps.core.services.telegram_group_test_service.Bot")
    def test_successful_group_access(self, mock_bot_class, service):
        """Test successful group access returns group info."""
        # Setup mock
        mock_chat = MagicMock()
        mock_chat.type = "supergroup"
        mock_chat.title = "Test Group"
        mock_chat.member_count = 42

        mock_bot = MagicMock()
        mock_bot.get_chat = AsyncMock(return_value=mock_chat)
        mock_bot.session.close = AsyncMock()
        mock_bot_class.return_value = mock_bot

        result = service.test_group("-1001234567890")

        assert result.accessible is True
        assert result.group_title == "Test Group"
        assert result.group_type == "supergroup"
        assert result.member_count == 42

    @patch("apps.core.services.telegram_group_test_service.Bot")
    def test_private_chat_returns_not_a_group(self, mock_bot_class, service):
        """Test that private chat ID returns NOT_A_GROUP error."""
        mock_chat = MagicMock()
        mock_chat.type = "private"

        mock_bot = MagicMock()
        mock_bot.get_chat = AsyncMock(return_value=mock_chat)
        mock_bot.session.close = AsyncMock()
        mock_bot_class.return_value = mock_bot

        result = service.test_group("123456789")

        assert result.accessible is False
        assert result.error_code == "NOT_A_GROUP"

    @patch("apps.core.services.telegram_group_test_service.Bot")
    def test_group_not_found(self, mock_bot_class, service):
        """Test TelegramNotFound returns GROUP_NOT_FOUND error."""
        mock_bot = MagicMock()
        mock_bot.get_chat = AsyncMock(side_effect=TelegramNotFound(method=MagicMock(), message="Chat not found"))
        mock_bot.session.close = AsyncMock()
        mock_bot_class.return_value = mock_bot

        result = service.test_group("-1001234567890")

        assert result.accessible is False
        assert result.error_code == "GROUP_NOT_FOUND"

    @patch("apps.core.services.telegram_group_test_service.Bot")
    def test_bot_kicked(self, mock_bot_class, service):
        """Test TelegramForbiddenError returns BOT_KICKED error."""
        mock_bot = MagicMock()
        mock_bot.get_chat = AsyncMock(side_effect=TelegramForbiddenError(method=MagicMock(), message="Forbidden"))
        mock_bot.session.close = AsyncMock()
        mock_bot_class.return_value = mock_bot

        result = service.test_group("-1001234567890")

        assert result.accessible is False
        assert result.error_code == "BOT_KICKED"

    @patch("apps.core.services.telegram_group_test_service.Bot")
    def test_bot_not_member(self, mock_bot_class, service):
        """Test 'bot is not a member' error returns BOT_NOT_MEMBER."""
        mock_bot = MagicMock()
        mock_bot.get_chat = AsyncMock(
            side_effect=TelegramBadRequest(method=MagicMock(), message="Bad Request: bot is not a member")
        )
        mock_bot.session.close = AsyncMock()
        mock_bot_class.return_value = mock_bot

        result = service.test_group("-1001234567890")

        assert result.accessible is False
        assert result.error_code == "BOT_NOT_MEMBER"

    def test_no_bot_token_configured(self):
        """Test that missing bot token returns BOT_NOT_CONFIGURED error."""
        with patch.object(TelegramGroupTestService, "__init__", lambda self: None):
            svc = TelegramGroupTestService()
            svc.bot_token = None

            result = svc.test_group("-1001234567890")

            assert result.accessible is False
            assert result.error_code == "BOT_NOT_CONFIGURED"
```

**Step 2: Run tests**

Run: `cd /var/www/terminal-pro/backend && source .venv/bin/activate && pytest tests/core/test_telegram_group_test_service.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/core/test_telegram_group_test_service.py
git commit -m "test(telegram): add unit tests for TelegramGroupTestService"
```

---

### Task 4: Frontend - Test Button and Status Display

**Files:**
- Modify: `frontend/src/views/ContainerOwners.vue`

**Step 1: Add types and state for test functionality**

In the `<script setup>` section, after the existing interfaces, add:

```typescript
interface GroupTestResult {
  accessible: boolean;
  group_title?: string;
  group_type?: string;
  member_count?: number;
  error_code?: string;
  error_message?: string;
}

// Test state for create modal
const createTestLoading = ref(false);
const createTestResult = ref<GroupTestResult | null>(null);

// Test state for edit modal
const editTestLoading = ref(false);
const editTestResult = ref<GroupTestResult | null>(null);
```

**Step 2: Add test function**

After the state declarations, add:

```typescript
// Test telegram group access
const testTelegramGroup = async (groupId: string, isEdit: boolean) => {
  if (!groupId.trim()) {
    message.warning('Введите ID группы для проверки');
    return;
  }

  const loadingRef = isEdit ? editTestLoading : createTestLoading;
  const resultRef = isEdit ? editTestResult : createTestResult;

  try {
    loadingRef.value = true;
    resultRef.value = null;

    const response = await http.post<{ success: boolean; data: GroupTestResult }>(
      '/telegram/test-group/',
      { group_id: groupId }
    );

    resultRef.value = response.data;

    // Auto-fill group name on success
    if (response.data.accessible && response.data.group_title) {
      if (isEdit) {
        editForm.telegram_group_name = response.data.group_title;
      } else {
        createForm.telegram_group_name = response.data.group_title;
      }
      message.success('Бот имеет доступ к группе');
    }
  } catch (error) {
    resultRef.value = {
      accessible: false,
      error_code: 'REQUEST_FAILED',
      error_message: error instanceof Error ? error.message : 'Ошибка проверки',
    };
  } finally {
    loadingRef.value = false;
  }
};
```

**Step 3: Update handleCreateCancel to reset test state**

Update `handleCreateCancel`:
```typescript
const handleCreateCancel = () => {
  createModalVisible.value = false;
  createForm.name = '';
  createForm.telegram_group_id = '';
  createForm.telegram_group_name = '';
  createForm.notifications_enabled = false;
  createTestResult.value = null;
};
```

**Step 4: Update handleEditCancel to reset test state**

Update `handleEditCancel`:
```typescript
const handleEditCancel = () => {
  editModalVisible.value = false;
  editForm.id = 0;
  editForm.name = '';
  editForm.telegram_group_id = '';
  editForm.telegram_group_name = '';
  editForm.notifications_enabled = false;
  editTestResult.value = null;
};
```

**Step 5: Commit**

```bash
git add frontend/src/views/ContainerOwners.vue
git commit -m "feat(frontend): add telegram group test state and function"
```

---

### Task 5: Frontend - Update Create Modal Template

**Files:**
- Modify: `frontend/src/views/ContainerOwners.vue`

**Step 1: Add CheckCircleOutlined and CloseCircleOutlined icons**

Update the imports:
```typescript
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons-vue';
```

**Step 2: Update create modal template**

Replace the create modal's telegram section (lines 82-93) with:

```vue
      <a-divider>Telegram уведомления</a-divider>
      <a-form-item label="ID группы">
        <a-input-group compact>
          <a-input
            v-model:value="createForm.telegram_group_id"
            placeholder="-1001234567890 или @groupname"
            style="width: calc(100% - 80px);"
            @change="createTestResult = null"
          />
          <a-button
            type="primary"
            :loading="createTestLoading"
            @click="testTelegramGroup(createForm.telegram_group_id, false)"
          >
            Тест
          </a-button>
        </a-input-group>
        <!-- Test result display -->
        <div v-if="createTestResult" style="margin-top: 8px;">
          <a-alert
            v-if="createTestResult.accessible"
            type="success"
            show-icon
          >
            <template #message>
              <span><CheckCircleOutlined /> Бот имеет доступ к группе</span>
            </template>
            <template #description>
              <span>{{ createTestResult.group_title }} ({{ createTestResult.group_type }}{{ createTestResult.member_count ? `, ${createTestResult.member_count} участников` : '' }})</span>
            </template>
          </a-alert>
          <a-alert
            v-else
            type="error"
            show-icon
          >
            <template #message>
              <span><CloseCircleOutlined /> {{ createTestResult.error_message }}</span>
            </template>
          </a-alert>
        </div>
      </a-form-item>
      <a-form-item label="Название группы">
        <a-input v-model:value="createForm.telegram_group_name" placeholder="Заполняется автоматически при тесте" />
      </a-form-item>
      <a-form-item label="Уведомления">
        <a-switch v-model:checked="createForm.notifications_enabled" />
        <span style="margin-left: 8px;">{{ createForm.notifications_enabled ? 'Включены' : 'Выключены' }}</span>
      </a-form-item>
```

**Step 3: Commit**

```bash
git add frontend/src/views/ContainerOwners.vue
git commit -m "feat(frontend): add test button to create modal"
```

---

### Task 6: Frontend - Update Edit Modal Template

**Files:**
- Modify: `frontend/src/views/ContainerOwners.vue`

**Step 1: Update edit modal template**

Replace the edit modal's telegram section (lines 108-119) with:

```vue
      <a-divider>Telegram уведомления</a-divider>
      <a-form-item label="ID группы">
        <a-input-group compact>
          <a-input
            v-model:value="editForm.telegram_group_id"
            placeholder="-1001234567890 или @groupname"
            style="width: calc(100% - 80px);"
            @change="editTestResult = null"
          />
          <a-button
            type="primary"
            :loading="editTestLoading"
            @click="testTelegramGroup(editForm.telegram_group_id, true)"
          >
            Тест
          </a-button>
        </a-input-group>
        <!-- Test result display -->
        <div v-if="editTestResult" style="margin-top: 8px;">
          <a-alert
            v-if="editTestResult.accessible"
            type="success"
            show-icon
          >
            <template #message>
              <span><CheckCircleOutlined /> Бот имеет доступ к группе</span>
            </template>
            <template #description>
              <span>{{ editTestResult.group_title }} ({{ editTestResult.group_type }}{{ editTestResult.member_count ? `, ${editTestResult.member_count} участников` : '' }})</span>
            </template>
          </a-alert>
          <a-alert
            v-else
            type="error"
            show-icon
          >
            <template #message>
              <span><CloseCircleOutlined /> {{ editTestResult.error_message }}</span>
            </template>
          </a-alert>
        </div>
      </a-form-item>
      <a-form-item label="Название группы">
        <a-input v-model:value="editForm.telegram_group_name" placeholder="Заполняется автоматически при тесте" />
      </a-form-item>
      <a-form-item label="Уведомления">
        <a-switch v-model:checked="editForm.notifications_enabled" />
        <span style="margin-left: 8px;">{{ editForm.notifications_enabled ? 'Включены' : 'Выключены' }}</span>
      </a-form-item>
```

**Step 2: Commit**

```bash
git add frontend/src/views/ContainerOwners.vue
git commit -m "feat(frontend): add test button to edit modal"
```

---

### Task 7: Frontend - Save Validation Logic

**Files:**
- Modify: `frontend/src/views/ContainerOwners.vue`

**Step 1: Add Modal import for confirm dialog**

The `Modal` is already imported from ant-design-vue.

**Step 2: Replace handleCreateSubmit with validation logic**

Replace `handleCreateSubmit`:

```typescript
const handleCreateSubmit = async () => {
  if (!createForm.name.trim()) {
    message.error('Пожалуйста, введите название');
    return;
  }

  // If group_id is provided, test it before saving
  if (createForm.telegram_group_id.trim()) {
    createTestLoading.value = true;
    try {
      const response = await http.post<{ success: boolean; data: GroupTestResult }>(
        '/telegram/test-group/',
        { group_id: createForm.telegram_group_id }
      );
      createTestResult.value = response.data;

      if (!response.data.accessible) {
        if (createForm.notifications_enabled) {
          // Block save if notifications enabled and test failed
          message.error('Невозможно сохранить: бот не имеет доступа к группе. Добавьте бота в группу или отключите уведомления.');
          createTestLoading.value = false;
          return;
        } else {
          // Warn but allow save if notifications disabled
          createTestLoading.value = false;
          Modal.confirm({
            title: 'Бот не имеет доступа к группе',
            content: 'Уведомления не будут отправляться. Сохранить всё равно?',
            okText: 'Сохранить',
            cancelText: 'Отмена',
            async onOk() {
              await doCreateSubmit();
            },
          });
          return;
        }
      } else {
        // Auto-fill group name on successful test
        if (response.data.group_title) {
          createForm.telegram_group_name = response.data.group_title;
        }
      }
    } catch (error) {
      message.error('Ошибка проверки группы');
      createTestLoading.value = false;
      return;
    }
    createTestLoading.value = false;
  }

  await doCreateSubmit();
};

const doCreateSubmit = async () => {
  try {
    createLoading.value = true;

    await http.post('/terminal/owners/', {
      name: createForm.name,
      telegram_group_id: createForm.telegram_group_id || null,
      telegram_group_name: createForm.telegram_group_name,
      notifications_enabled: createForm.notifications_enabled,
    });

    message.success('Собственник успешно создан');
    createModalVisible.value = false;
    createTestResult.value = null;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка создания собственника');
  } finally {
    createLoading.value = false;
  }
};
```

**Step 3: Commit**

```bash
git add frontend/src/views/ContainerOwners.vue
git commit -m "feat(frontend): add save validation for create modal"
```

---

### Task 8: Frontend - Edit Modal Save Validation

**Files:**
- Modify: `frontend/src/views/ContainerOwners.vue`

**Step 1: Replace handleEditSubmit with validation logic**

Replace `handleEditSubmit`:

```typescript
const handleEditSubmit = async () => {
  if (!editForm.name.trim()) {
    message.error('Пожалуйста, введите название');
    return;
  }

  // If group_id is provided, test it before saving
  if (editForm.telegram_group_id.trim()) {
    editTestLoading.value = true;
    try {
      const response = await http.post<{ success: boolean; data: GroupTestResult }>(
        '/telegram/test-group/',
        { group_id: editForm.telegram_group_id }
      );
      editTestResult.value = response.data;

      if (!response.data.accessible) {
        if (editForm.notifications_enabled) {
          // Block save if notifications enabled and test failed
          message.error('Невозможно сохранить: бот не имеет доступа к группе. Добавьте бота в группу или отключите уведомления.');
          editTestLoading.value = false;
          return;
        } else {
          // Warn but allow save if notifications disabled
          editTestLoading.value = false;
          Modal.confirm({
            title: 'Бот не имеет доступа к группе',
            content: 'Уведомления не будут отправляться. Сохранить всё равно?',
            okText: 'Сохранить',
            cancelText: 'Отмена',
            async onOk() {
              await doEditSubmit();
            },
          });
          return;
        }
      } else {
        // Auto-fill group name on successful test
        if (response.data.group_title) {
          editForm.telegram_group_name = response.data.group_title;
        }
      }
    } catch (error) {
      message.error('Ошибка проверки группы');
      editTestLoading.value = false;
      return;
    }
    editTestLoading.value = false;
  }

  await doEditSubmit();
};

const doEditSubmit = async () => {
  try {
    editLoading.value = true;

    await http.patch(`/terminal/owners/${editForm.id}/`, {
      name: editForm.name,
      telegram_group_id: editForm.telegram_group_id || null,
      telegram_group_name: editForm.telegram_group_name,
      notifications_enabled: editForm.notifications_enabled,
    });

    message.success('Собственник успешно обновлён');
    editModalVisible.value = false;
    editTestResult.value = null;
    refresh();
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка обновления собственника');
  } finally {
    editLoading.value = false;
  }
};
```

**Step 2: Run TypeScript check**

Run: `cd /var/www/terminal-pro/frontend && npm run build`
Expected: Build completes successfully

**Step 3: Commit**

```bash
git add frontend/src/views/ContainerOwners.vue
git commit -m "feat(frontend): add save validation for edit modal"
```

---

### Task 9: Production Deployment

**Step 1: Restart backend service**

Run: `sudo systemctl restart mtt-terminal`
Expected: Service restarts successfully

**Step 2: Build frontend for production**

Run: `cd /var/www/terminal-pro/frontend && npm run build`
Expected: Build completes successfully

**Step 3: Verify backend is running**

Run: `sudo systemctl status mtt-terminal`
Expected: Active (running)

**Step 4: Test API endpoint**

Run: `curl -X POST https://mtt-pro-api.xlog.uz/api/telegram/test-group/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"group_id": "-1001234567890"}'`
Expected: Returns JSON response with accessible or error info

---

### Task 10: Final Verification

**Step 1: Manual testing checklist**

- [ ] Open ContainerOwners page
- [ ] Create new owner - test "Тест" button with valid group ID
- [ ] Verify group name auto-fills
- [ ] Try to save with notifications ON and invalid group - should block
- [ ] Try to save with notifications OFF and invalid group - should warn
- [ ] Edit existing owner - repeat tests

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat(telegram): complete group access test feature

- Add TelegramGroupTestService for testing bot access to groups
- Add POST /api/telegram/test-group/ endpoint
- Add test button and validation to ContainerOwners.vue
- Auto-fill group name from Telegram on successful test
- Block save if notifications enabled and test fails
- Warn but allow save if notifications disabled"
```
