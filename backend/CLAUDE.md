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
- [ ] API docs: `http://localhost:8000/api/docs/`

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

### Database Switching
The project automatically switches between SQLite (local) and PostgreSQL (Docker) based on the `DATABASE_URL` environment variable. This is configured in `terminal_app/settings.py:94-110`.

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

Web-based API for customer access to container and pre-order management. Customers authenticate with username + password and can view their company's data.

### Authentication

**Login Endpoint:** `POST /api/auth/login/`

```bash
# Customer login with username + password
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"login": "customer_username", "password": "password123"}'
```

**Response:**
```json
{
  "success": true,
  "user_type": "customer",
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci...",
  "user": {
    "id": 105,
    "username": "customer_username",
    "full_name": "Customer Name",
    "phone_number": "+998901234567",
    "company": {
      "id": 25,
      "name": "Company Name",
      "slug": "company-name"
    },
    "is_active": true
  }
}
```

**Use token in all requests:**
```bash
Authorization: Bearer <access_token>
```

### Customer Portal Endpoints

All customer endpoints require JWT authentication with `user_type='customer'`.

#### Profile Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customer/profile/` | GET | Get customer profile with company info |
| `/api/customer/profile/update_profile/` | PATCH | Update name or password |

**Update profile example:**
```bash
curl -X PATCH http://localhost:8000/api/customer/profile/update_profile/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "New", "last_name": "Name", "password": "newpass123"}'
```

#### Container Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customer/containers/` | GET | List company's containers (supports all filters) |
| `/api/customer/containers/{id}/` | GET | Get container entry details |

**Features:**
- Automatic company filtering (customers only see their company's containers)
- Supports all `ContainerEntryFilter` parameters (status, transport_type, dates, etc.)
- Default ordering: newest entries first (`-entry_time`)

**List containers example:**
```bash
# List all company containers
curl http://localhost:8000/api/customer/containers/ \
  -H "Authorization: Bearer <token>"

# Filter by status and date
curl "http://localhost:8000/api/customer/containers/?status=LADEN&entry_time_after=2025-01-01" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "count": 10,
  "next": "http://localhost:8000/api/customer/containers/?page=2",
  "previous": null,
  "results": [
    {
      "id": 123,
      "container_number": "HDMU6565958",
      "container_type": "20GP",
      "container_size": "20",
      "status": "LADEN",
      "entry_time": "2025-12-23T10:00:00+05:00",
      "exit_date": null,
      "dwell_time_days": 5,
      "transport_type": "TRUCK",
      "transport_number": "01A123BC",
      "client_name": "Client Name",
      "cargo_name": "Cargo Description",
      "cargo_weight": 15000,
      "location": "Zone K1",
      "container_owner_name": "Owner Name",
      "company": {
        "id": 25,
        "name": "Company Name",
        "slug": "company-name"
      }
    }
  ]
}
```

#### Pre-Order Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customer/preorders/` | GET | List customer's pre-orders |
| `/api/customer/preorders/` | POST | Create new pre-order |
| `/api/customer/preorders/{id}/` | GET | Get pre-order details |
| `/api/customer/preorders/{id}/` | PATCH | Update pre-order notes |
| `/api/customer/preorders/{id}/` | DELETE | Cancel pre-order (PENDING only) |
| `/api/customer/preorders/pending/` | GET | Get pending pre-orders only |

**Create pre-order example:**
```bash
curl -X POST http://localhost:8000/api/customer/preorders/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "plate_number": "01A123BC",
    "operation_type": "LOAD",
    "notes": "Optional notes"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 81,
    "plate_number": "01A123BC",
    "operation_type": "LOAD",
    "status": "PENDING",
    "status_display": "Ожидает",
    "truck_photo": null,
    "notes": "Optional notes",
    "vehicle_entry": null,
    "created_at": "2025-12-23T16:36:44+05:00",
    "matched_at": null,
    "cancelled_at": null,
    "batch_id": null
  }
}
```

**Cancel pre-order example:**
```bash
curl -X DELETE http://localhost:8000/api/customer/preorders/81/ \
  -H "Authorization: Bearer <token>"
```

### Security & Data Isolation

**Automatic company filtering:**
- Customers can ONLY see containers belonging to their company
- Company filter applied at queryset level (cannot be bypassed)
- No need to specify company_id in requests

**Pre-order ownership:**
- Customers can ONLY see their own pre-orders
- Cannot access other customers' pre-orders (404 response)

**Permission classes:**
- `IsCustomer` - Blocks admin/manager users from customer endpoints
- `IsCustomerOwner` - Ensures customer owns the resource
- `HasCompanyAccess` - Validates company membership

**Rate limiting:**
- Customer endpoints: 500 requests/hour
- Admin/staff endpoints: 1000 requests/hour
- Configured in `terminal_app/settings.py:192-196`

### Creating Customer Users

**Via Django shell:**
```python
from apps.accounts.models import CustomUser, Company, CustomerProfile

# Get company
company = Company.objects.get(name="Your Company")

# Create customer with username and password
customer = CustomUser.objects.create_user(
    username="customer_username",
    password="password123",
    user_type="customer",
    first_name="First",
    last_name="Last",
    is_active=True
)

# Link to company via profile
CustomerProfile.objects.create(
    user=customer,
    company=company,
    phone_number="+998901234567",
    bot_access=True  # Optional: for Telegram bot access
)
```

**Via Admin API** (requires admin JWT):
```bash
curl -X POST http://localhost:8000/api/auth/customers/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "First",
    "last_name": "Last",
    "phone_number": "+998901234567",
    "company_id": 1,
    "bot_access": false,
    "username": "customer_username",
    "password": "password123"
  }'
```

### Implementation Details

**Location:** `apps/customer_portal/`
- `permissions.py` - Customer permission classes
- `serializers.py` - Customer-facing serializers (hides admin fields)
- `views.py` - Thin viewsets that call existing services
- `urls.py` - Customer endpoint routing

**Service reuse:**
- Uses existing `CustomerService` from `apps/accounts/services/customer_service.py`
- Uses existing `PreOrderService` from `apps/terminal_operations/services/preorder_service.py`
- Uses existing `ContainerEntryFilter` from `apps/terminal_operations/filters.py`
- No code duplication - customer endpoints are thin wrappers with customer permissions

**Testing:**
- Unit tests: `tests/customer_portal/test_permissions.py` (10 tests)
- API tests: `tests/customer_portal/test_api.py` (21 tests)
- Auth tests: `tests/customer_portal/test_authentication.py` (13 tests)
- Run: `pytest tests/customer_portal/ -v`

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

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| Migration conflicts | `python manage.py makemigrations --merge` |
| Bot language wrong | Check `state.data['language']` in FSM state |
| Excel import fails | Ensure 20 columns, check import service logs |
| Plate API error | Set `PLATE_RECOGNIZER_API_KEY` in `.env` |
| Filters not working | Use `__icontains` for partial matches |
| Service tests fail | Call methods via service instance, not models |
