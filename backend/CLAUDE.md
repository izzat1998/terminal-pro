# CLAUDE.md - MTT Backend

This file provides guidance to Claude Code (claude.ai/code) when working with the backend codebase.

## Memory Triggers

**Before writing any code, remember:**

| Pattern | Rule |
|---------|------|
| Python commands | ALWAYS use `.venv/bin/python` or activate venv first (`source .venv/bin/activate`) |
| Business logic | ALL logic goes in services (`apps/*/services/`), NOT in views or serializers |
| Error handling | Use custom exceptions from `apps/core/exceptions.py` |
| User types | admin (API), manager (Telegram), customer (web portal) |
| Language | Russian for user-facing messages, English for code/comments |
| Validation | Validate in services, fail fast with descriptive errors |
| Testing | Add tests in `tests/` for new functionality |

## Quick Reference

### Create New Feature Checklist

1. **Model** - Add/update in `apps/<app>/models.py`
2. **Migration** - `python manage.py makemigrations`
3. **Service** - Add business logic in `apps/<app>/services/`
4. **Serializer** - Add in `apps/<app>/serializers.py`
5. **View** - Thin orchestration in `apps/<app>/views.py`
6. **URL** - Register in `apps/<app>/urls.py`
7. **Tests** - Add in `tests/<app>/`

### Debug Checklist

- [ ] Check service layer logs
- [ ] Verify JWT token is valid (1 hour expiry)
- [ ] Django shell: `python manage.py shell`
- [ ] View raw SQL: `print(queryset.query)`
- [ ] API docs: `http://localhost:8008/api/docs/`

### Common Service Pattern

```python
# apps/<app>/services/<feature>_service.py
from apps.core.services.base_service import BaseService
from apps.core.exceptions import BusinessLogicError

class FeatureService(BaseService):
    def create_item(self, data: dict, user) -> Model:
        # 1. Validate
        if not data.get('required_field'):
            raise BusinessLogicError("Field is required")

        # 2. Business logic
        item = Model.objects.create(**data, created_by=user)

        # 3. Log and return
        self.logger.info(f"Created item {item.id}")
        return item
```

---

## Project Overview

Django REST API for managing container terminal operations - tracking container entries/exits, status changes (laden/empty), transport information (truck/wagon), and documentation images.

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Database setup
python manage.py migrate
python manage.py create_admin  # Creates default admin user
```

### Running the Application
```bash
# Local development (SQLite)
python manage.py runserver

# Run Telegram bot (requires TELEGRAM_BOT_TOKEN in .env)
python manage.py run_telegram_bot
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps

# Run specific test markers
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Data Management
```bash
# Seed database with test data
python manage.py seed_data

# Optional parameters for seed_data
python manage.py seed_data --containers 100 --entries 200 --users 10 --clear

# Seed file categories (for files app)
python manage.py seed_file_categories
```

## Architecture

### Database
Local development and production both use **PostgreSQL** via the `DATABASE_URL` environment variable. SQLite is only a fallback when `DATABASE_URL` is not set. Configured in `terminal_app/settings.py:113-132`.

### Service Layer Pattern
Business logic lives in service classes (not views/models). All services inherit from `BaseService` (`apps/core/services/base_service.py`) which provides logging. Examples:
- `apps/containers/services/container_service.py`
- `apps/terminal_operations/services/container_entry_service.py`

### Centralized Error Handling
Custom exception handler in `apps/core/exceptions.py` provides consistent error responses across all API endpoints:
- Business logic errors: `BusinessLogicError`, `ContainerNotFoundError`, `DuplicateEntryError`, `InvalidContainerStateError`
- All errors return: `{success: false, error: {code, message, details?}, timestamp}`
- Configured via `REST_FRAMEWORK['EXCEPTION_HANDLER']` in settings

### App Structure
- **accounts**: JWT authentication, custom user model (`CustomUser` extends `AbstractUser`) with three user types: `admin`, `manager`, `customer`
- **containers**: Container model with ISO container number validation (4 letters + 7 digits)
- **core**: Shared utilities, `TimestampedModel` base class, error handling, `BaseService`
- **terminal_operations**: `ContainerEntry` records with status tracking, `CraneOperation` for crane ops, `PreOrder` for customer pre-orders with gate matching
- **vehicles**: Vehicle entry/exit tracking with `VehicleEntry` (workflow: WAITING→ON_TERMINAL→EXITED) and `Destination` with terminal zones
- **files**: Centralized file management with `File`, `FileCategory`, and `FileAttachment` models (generic file attachments using ContentTypes)
- **customer_portal**: Customer web API endpoints with company-scoped permissions (thin wrappers around existing services)
- **billing**: Monthly statements, on-demand invoices, tariffs, storage cost calculations, additional charges, multi-currency (USD/UZS) with CBU exchange rates, Excel/PDF export
- **gate**: Hikvision ANPR camera integration with `ANPRDetection` model, PTZ camera control, `GateConsumer` WebSocket for real-time gate events (JWT-authenticated)

### User Types
- **admin**: Full system access, can manage all users, API access via username + password
- **manager**: Telegram bot access for container/vehicle operations at terminal, API access via phone + password
- **customer**: Web portal + Telegram bot access for viewing containers and managing pre-orders, API access via username + password

### Key Relationships

```text
CustomUser (accounts) ─────────────────────────────────────────────────
    │ user_type: admin | manager | customer
    │
    ├─ recorded_by ──→ ContainerEntry (terminal_operations)
    │                      ↓ container (PROTECT)
    │                  Container (containers)
    │                      ↓ entry (CASCADE)
    │                  ContainerEntryImage
    │                      ↓ container_entry (CASCADE)
    │                  CraneOperation
    │
    ├─ customer ─────→ PreOrder (terminal_operations)
    │                      ↓ matched_entry
    │                  ContainerEntry
    │
    └─ customer ─────→ VehicleEntry (vehicles)
                           ↓ destination
                       Destination (zones: K1, K2, H1, etc.)
```

## AI Assistant Guidelines

### DO
- Use service layer for all business logic (never put logic in views/serializers)
- Follow centralized error handling patterns (raise `BusinessLogicError` subclasses)
- Add tests for new endpoints (use pytest fixtures in `tests/conftest.py`)
- Use Russian for user-facing messages, English for code/comments
- Check existing patterns before creating new abstractions

### NEVER
- Modify existing migration files (always create new migrations)
- Bypass service layer in views (views should be thin orchestration)
- Store sensitive data in logs (phone numbers, tokens, etc.)
- Use Russian text in Python code (variable names, function names, comments)
- Create duplicate logic (check for existing services/utilities first)
- Skip validation in service layer (validate early, fail fast)

### Security Reminders
- Container numbers are validated via ISO format (4 letters + 7 digits)
- JWT tokens expire after 1 hour (refresh tokens after 7 days)
- Telegram bot access controlled via `bot_access` flag on `CustomUser`
- All file uploads have size limits (images: 5MB, Excel: 10MB)

## API Documentation Pattern

**All API endpoints follow these conventions:**

### Authentication
- Required: JWT Bearer token (obtained via `/api/auth/login/`)
- Header: `Authorization: Bearer <token>`
- Exceptions: Login, register, and public endpoints

### Standard Response Format
```json
// Success
{
  "success": true,
  "data": {...},
  "message": "Optional success message"
}

// Error
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error",
    "details": {...}  // Optional validation errors
  },
  "timestamp": "2025-11-21T10:30:00Z"
}
```

### Common HTTP Status Codes
- `200 OK` - Successful GET/PUT/POST
- `201 Created` - Successful resource creation
- `400 Bad Request` - Validation error or business logic violation
- `401 Unauthorized` - Missing or invalid JWT token
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Unexpected server error

## API Endpoints

Full API documentation available at `/api/docs/` (Swagger) or `/api/redoc/` (ReDoc).

| Route Prefix | Description |
|-------------|-------------|
| `/api/auth/` | Authentication (login, register, refresh, managers, customers) |
| `/api/terminal/` | Container entries, crane operations, preorders, plate recognition |
| `/api/vehicles/` | Vehicle entries, destinations, statistics |
| `/api/files/` | File uploads and attachments |
| `/api/customer/` | Customer web portal (containers, pre-orders, profile) |
| `/api/billing/` | Statements, invoices, tariffs, storage costs, exports |
| `/api/gate/` | ANPR detections, camera control, gate events |

### Key Implementation Details

**Crane Operations:** Include `crane_operations_data` array when creating container entries:

```json
{
  "container_number": "HDMU6565958",
  "crane_operations_data": [{"operation_date": "2025-10-28T10:30:00Z"}]
}
```

**Excel Import:** `POST /api/terminal/entries/import_excel/` - 20 column format, handles duplicates automatically. Implementation: `apps/terminal_operations/services/container_entry_import_service.py`

**Plate Recognition:** Requires `PLATE_RECOGNIZER_API_KEY` in `.env`. Supports regions: `uz`, `ru`, `us`, `eu`, etc. Implementation: `telegram_bot/services/plate_recognizer_service.py`

**PreOrders:** Customer pre-orders at `/api/terminal/preorders/` with workflow: PENDING → MATCHED → COMPLETED. Gate matching via `apps/terminal_operations/services/gate_matching_service.py`

**Vehicle Entries:** `/api/vehicles/entries/` with workflow: WAITING → ON_TERMINAL → EXITED. Includes destination zones (K1, K2, H1, etc.)

## Search & Filter API

Container entries at `/api/terminal/entries/` support comprehensive filtering. Implementation: `apps/terminal_operations/filters.py:ContainerEntryFilter`

| Filter Type | Examples |
|------------|----------|
| Full-text search | `?search_text=HDMU6565958` |
| Status/transport | `?status=LADEN&transport_type=TRUCK` (English or Russian) |
| Owner | `?container_owner_id=2` or `?container_owner_ids=1,2,3` |
| Date ranges | `?entry_date_after=2025-01-01&entry_date_before=2025-12-31` |
| Numeric ranges | `?cargo_weight_range=100-500&dwell_time_range=5-30` |
| Partial match | `?client_name__icontains=Client` |
| Exit status | `?has_exited=true` |
| Sorting | `?ordering=-entry_time` |

**Search fields:** container number/type/size, transport numbers, client name, cargo name, destination, notes, recorded_by user info

## Customer Web Portal API

Customer endpoints at `/api/customer/` require JWT with `user_type='customer'`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customer/profile/` | GET | Customer profile with company info |
| `/api/customer/profile/update_profile/` | PATCH | Update name or password |
| `/api/customer/containers/` | GET | Company containers (all `ContainerEntryFilter` params supported) |
| `/api/customer/preorders/` | GET/POST | List/create pre-orders |
| `/api/customer/preorders/{id}/` | GET/PATCH/DELETE | Manage pre-order (cancel only if PENDING) |

**Security:** Automatic company-scoped filtering at queryset level. Permission classes: `IsCustomer`, `IsCustomerOwner`, `HasCompanyAccess`.

**Implementation:** `apps/customer_portal/` — thin viewsets wrapping existing services (`CustomerService`, `PreOrderService`, `ContainerEntryFilter`). Tests: `pytest tests/customer_portal/ -v` (44 tests).

Full request/response examples: `http://localhost:8008/api/docs/`

## Telegram Bot

Multi-language bot (Russian/Uzbek) for container and vehicle operations. Access via phone verification.

**Registration:** `/start` → language selection → share phone → validated against `CustomUser` with `bot_access=True`

**Access control:**
- Middleware: `telegram_bot/middleware.py:ManagerAccessMiddleware`
- Decorator: `@require_manager_access`
- Checks: user exists → `is_active=True` → `bot_access=True` → Telegram ID linked

**Manager API:** `/api/managers/` (admin only)
- `POST /` - Create manager with `phone_number`, `bot_access`
- `POST /{id}/grant-access/` / `POST /{id}/revoke-access/`
- `DELETE /{id}/` - Soft delete (sets `is_active=False`)

**Customer API:** `/api/customers/` - Same pattern for customer user type

**Key files:**
- Handlers: `telegram_bot/handlers/`
- Translations: `telegram_bot/translations.py`
- Services: `apps/accounts/services/manager_service.py`, `customer_service.py`

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `ALLOWED_HOSTS` - Comma-separated allowed hosts
- `DATABASE_URL` - PostgreSQL connection (optional, defaults to SQLite)
- `REDIS_URL` - Redis connection for caching (optional)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` - Redis for Telegram bot
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `PLATE_RECOGNIZER_API_KEY` - PlateRecognizer.com API key

### JWT Configuration
- Access token: 1 hour
- Refresh token: 7 days (with rotation and blacklisting)
- Settings: `terminal_app/settings.py:188-198`

### Localization
- Language: Russian (`LANGUAGE_CODE = 'ru'`)
- Timezone: Asia/Tashkent (`TIME_ZONE = 'Asia/Tashkent'`)
- User-facing messages in Russian

### Media Files
Images organized by date: `media/container_entries/{year}/{month}/{entry_id}_{filename}`

## Testing

Test suite in `tests/` with pytest configuration in `pytest.ini`. Uses Django test database and fixtures in `tests/conftest.py`.

## Billing Gotchas

- Residual billing: iterate `cost_result.periods` for date overlap — never blindly use `periods[-1]`
- On-demand invoices: admin-only feature (customer portal has no invoice creation endpoint)
- `safe_int_param()` for all query params from user input; Django URL path params are already safe

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| Migration conflicts | `python manage.py makemigrations --merge` |
| Bot language wrong | Check `state.data['language']` in FSM state |
| Excel import fails | Ensure 20 columns, check import service logs |
| Plate API error | Set `PLATE_RECOGNIZER_API_KEY` in `.env` |
| Filters not working | Use `__icontains` for partial matches |
| Service tests fail | Call methods via service instance, not models |
