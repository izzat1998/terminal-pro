# Billing Statements Redesign — Master Table with Payment Status

**Date:** 2026-01-27
**Status:** Approved

## Summary

Replace the current "select month → generate → view" billing workflow with a master table showing all generated statements at a glance, with payment status tracking and inline detail expansion.

## Backend Changes

### 1. Model: Add payment fields to `MonthlyStatement`

```python
# apps/billing/models.py — new fields on MonthlyStatement
payment_status = CharField(choices=[("unpaid", "Не оплачен"), ("paid", "Оплачен")], default="unpaid")
paid_at = DateTimeField(null=True, blank=True)
paid_marked_by = ForeignKey("accounts.CustomUser", null=True, blank=True, on_delete=SET_NULL)
```

### 2. Migration

New migration adding the 3 fields.

### 3. Serializer Updates

- `MonthlyStatementSerializer` — add `payment_status`, `paid_at`, `paid_marked_by` fields
- Add `MonthlyStatementListSerializer` — lightweight serializer for master table (no line_items, just summary + payment status)

### 4. API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `GET /api/billing/statements/` | GET | Admin | List all statements, filterable by `company_id`, `year` |
| `POST /api/billing/statements/{id}/mark-paid/` | POST | Admin | Toggle payment status |
| `GET /api/customer/billing/statements/` | GET | Customer | List own company statements (existing, add payment_status) |

### 5. Service Updates

- `MonthlyStatementService.list_statements()` — already exists, ensure it returns payment fields
- `MonthlyStatementService.mark_paid()` — new method to toggle payment status

## Frontend Changes

### 1. Rewrite `MonthlyStatements.vue`

Replace select-month workflow with master table:

- **Master table columns:** Period (month/year), Containers count, Total USD, Total UZS, Payment Status
- **Year filter** dropdown at top (default: current year)
- **Expandable rows** — click row to show line items table + export buttons inline
- **Admin mode** (`companySlug` prop present): status column has clickable toggle + "Generate" button for new months
- **Customer mode** (no `companySlug`): status column is read-only badge

### 2. No new components

- Rewrite `MonthlyStatements.vue` in place
- Keep `CurrentCosts` tab unchanged
- Keep `CustomerBilling.vue` and `CompanyBilling.vue` wrappers unchanged

## Implementation Order

1. Backend: migration + model fields
2. Backend: serializer + API endpoints
3. Backend: service method for mark-paid
4. Frontend: rewrite MonthlyStatements.vue
