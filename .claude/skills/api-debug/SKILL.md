---
name: api-debug
description: Use this skill when debugging API issues, testing endpoints, checking backend health, or troubleshooting authentication problems in the MTT project
---

# API Debug Skill

Automatically debug and test API endpoints for the MTT project.

## When to Use This Skill

Claude should invoke this skill when:
- User reports API errors (401, 403, 404, 500)
- User asks to test an endpoint
- User has authentication issues
- Backend connection problems occur
- User wants to inspect API responses

## Health Check

First, verify the backend is running:

```bash
curl -s http://localhost:8000/api/docs/ -o /dev/null -w "%{http_code}"
```

If connection refused, instruct user to start backend:
```bash
make backend
```

## Authentication

Test login and retrieve JWT tokens:

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"login": "USERNAME", "password": "PASSWORD"}'
```

Response format:
```json
{
  "success": true,
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci...",
  "user_type": "admin|manager|customer"
}
```

## Making Authenticated Requests

GET request:
```bash
TOKEN="access_token_here"
curl http://localhost:8000/api/terminal/entries/ \
  -H "Authorization: Bearer $TOKEN"
```

POST request:
```bash
curl -X POST http://localhost:8000/api/terminal/entries/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"container_number": "HDMU6565958", "status": "LADEN"}'
```

## Key API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/auth/` | Authentication, user management |
| `/api/terminal/` | Container entries, crane ops, preorders |
| `/api/vehicles/` | Vehicle tracking |
| `/api/files/` | File uploads |
| `/api/customer/` | Customer portal |

## Response Format

Success:
```json
{"success": true, "data": {...}}
```

Error:
```json
{"success": false, "error": {"code": "ERROR_CODE", "message": "..."}}
```

## Troubleshooting Guide

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Backend not running | `make backend` |
| 401 Unauthorized | Invalid/expired token | Re-authenticate |
| 403 Forbidden | Wrong user type | Check permissions |
| 404 Not Found | Wrong URL | Check `/api/docs/` |
| 500 Server Error | Backend crash | Check logs |

## Documentation Links

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/
