# Login Error Response Documentation

This document shows the comprehensive error response structure for the login API endpoint after aligning with the centralized error handling system.

## Endpoint
```
POST /api/auth/login/
```

## Error Response Structure

All errors follow the centralized format defined in `apps/core/exceptions.py`:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {} // Optional, only present for validation errors
  },
  "timestamp": "2025-11-20T12:34:56.789Z"
}
```

## Error Scenarios

### 1. Missing Credentials (400 Bad Request)

**Request:**
```json
{
  "login": "",
  "password": ""
}
```

**Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Ошибка валидации. Проверьте детали для конкретных полей.",
    "details": {
      "non_field_errors": ["Необходимо указать логин и пароль"]
    }
  },
  "timestamp": "2025-11-20T12:34:56.789Z"
}
```

**Exception Used:** `serializers.ValidationError`
**Reason:** Input validation failure (missing required fields)

---

### 2. Wrong Username/Phone (401 Unauthorized)

**Request (wrong username):**
```json
{
  "login": "wronguser",
  "password": "somepassword"
}
```

**Request (wrong phone):**
```json
{
  "login": "+998901234567",
  "password": "somepassword"
}
```

**Response:**
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Неверный логин или пароль"
  },
  "timestamp": "2025-11-20T12:34:56.789Z"
}
```

**Exception Used:** `AuthenticationFailed`
**Reason:** User/manager not found or wrong password

---

### 3. Wrong Password (401 Unauthorized)

**Request:**
```json
{
  "login": "existinguser",
  "password": "wrongpassword"
}
```

**Response:**
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Неверный логин или пароль"
  },
  "timestamp": "2025-11-20T12:34:56.789Z"
}
```

**Exception Used:** `AuthenticationFailed`
**Reason:** Password verification failed

**Security Note:** We intentionally use the same message for "user not found" and "wrong password" to prevent username enumeration attacks.

---

### 4. Inactive Account - CustomUser (403 Forbidden)

**Request:**
```json
{
  "login": "inactiveuser",
  "password": "correctpassword"
}
```

**Response:**
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Учётная запись пользователя отключена"
  },
  "timestamp": "2025-11-20T12:34:56.789Z"
}
```

**Exception Used:** `PermissionDenied`
**Reason:** Account exists and password is correct, but `is_active=False`

---

### 5. Inactive Account - Manager (403 Forbidden)

**Request:**
```json
{
  "login": "+998901234567",
  "password": "correctpassword"
}
```

**Response:**
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Учётная запись менеджера отключена"
  },
  "timestamp": "2025-11-20T12:34:56.789Z"
}
```

**Exception Used:** `PermissionDenied`
**Reason:** Manager exists and password is correct, but `is_active=False`

---

## Exception Hierarchy

The login serializers now use semantically correct exceptions:

### Input Validation
- **Exception:** `serializers.ValidationError`
- **HTTP Status:** 400 Bad Request
- **Error Code:** `VALIDATION_ERROR`
- **Use Case:** Missing or malformed input (empty login/password)

### Authentication Failure
- **Exception:** `AuthenticationFailed` (from `rest_framework.exceptions`)
- **HTTP Status:** 401 Unauthorized
- **Error Code:** `AUTHENTICATION_FAILED`
- **Use Case:** Wrong credentials (user not found, wrong password)

### Permission Denied
- **Exception:** `PermissionDenied` (from `rest_framework.exceptions`)
- **HTTP Status:** 403 Forbidden
- **Error Code:** `PERMISSION_DENIED`
- **Use Case:** Correct credentials but account is inactive

---

## Implementation Details

### UnifiedLoginSerializer
- Line 51: Uses `ValidationError` for missing credentials
- Line 67: Uses `AuthenticationFailed` for wrong credentials
- Line 87: Uses `PermissionDenied` for inactive manager account
- Line 105: Uses `PermissionDenied` for inactive user account

### LoginSerializer
- Line 23: Uses `ValidationError` for missing credentials
- Line 27: Uses `AuthenticationFailed` for wrong credentials
- Line 30: Uses `PermissionDenied` for inactive account

### View Layer
- `/apps/accounts/views.py:37`: Uses `raise_exception=True` to propagate exceptions
- All exceptions are caught by the centralized handler in `apps/core/exceptions.py`

---

## Success Response (for comparison)

**Request:**
```json
{
  "login": "admin",
  "password": "correctpassword"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "user_type": "custom_user",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "first_name": "Admin",
    "last_name": "User",
    "is_admin": true,
    "is_staff": true,
    "is_active": true
  }
}
```

---

## Testing the Changes

### Test Wrong Credentials
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"login":"wronguser","password":"wrongpass"}' | jq
```

**Expected Error Code:** `AUTHENTICATION_FAILED`

### Test Inactive Account
```bash
# First create inactive user via Django admin or shell
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"login":"inactiveuser","password":"password"}' | jq
```

**Expected Error Code:** `PERMISSION_DENIED`

### Test Missing Credentials
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"login":"","password":""}' | jq
```

**Expected Error Code:** `VALIDATION_ERROR`

---

## Summary of Changes

### Before (Non-Centralized)
All login errors used `serializers.ValidationError`, resulting in:
- Generic `VALIDATION_ERROR` code for all failures
- Nested error messages in `details.non_field_errors`
- No semantic distinction between validation vs authentication failures

### After (Centralized)
Login errors use appropriate exceptions:
- `ValidationError` → Missing/malformed input → `VALIDATION_ERROR` (400)
- `AuthenticationFailed` → Wrong credentials → `AUTHENTICATION_FAILED` (401)
- `PermissionDenied` → Inactive account → `PERMISSION_DENIED` (403)
- Clean, top-level error messages (no nesting for auth failures)
- Semantically correct HTTP status codes
