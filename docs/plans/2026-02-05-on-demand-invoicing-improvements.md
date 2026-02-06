# On-Demand Invoicing Improvements

**Date:** 2026-02-05
**Status:** Approved
**Authors:** Finance team + Claude

## Overview

Improvements to the on-demand invoicing feature based on accounting review. Addresses revenue leakage, double-billing prevention, and audit requirements.

## Decisions Summary

| # | Topic | Decision |
|---|-------|----------|
| 1 | Active containers | Allow invoicing + automatic residual billing |
| 2 | Additional charges | No double-billing - system enforces |
| 3a | Draft invoices | Can be deleted entirely |
| 3b | Finalized cancellation | Require reason + audit fields |
| 4 | Payment tracking | Add reference + payment date |
| 5 | Tax/VAT | Not needed - 1C handles |

---

## 1. Automatic Residual Billing

### Problem
When an active container is invoiced on-demand, it may stay longer than the invoiced period. Without residual billing, those extra days are never billed = **revenue leakage**.

### Solution
Track "invoiced until" date. When container exits later, residual days go to monthly statement.

### Example
```
Container enters:     Jan 10
On-demand invoice:    Jan 25 (billed 15 days, $60)
Container exits:      Feb 5

Result:
- OD-2026-0001:       Jan 10-25, 12 billable days, $60
- Monthly statement:  Jan 26-Feb 5, 11 days, $55 (RESIDUAL)
- Total billed:       $115 ✓ (no leakage)
```

### Implementation

**Monthly statement service** - Change exclusion logic:

```python
# OLD: Exclude container entirely
entries = entries.exclude(
    on_demand_items__invoice__status__in=['draft', 'finalized', 'paid']
)

# NEW: Smart exclusion with residual calculation
for entry in entries:
    od_item = entry.on_demand_items.filter(
        invoice__status__in=['draft', 'finalized', 'paid']
    ).first()

    if od_item:
        if od_item.exit_date is not None:
            # Was exited when invoiced - exclude entirely
            continue
        else:
            # Was active when invoiced - check for residual
            invoiced_until = od_item.entry_date + timedelta(days=od_item.total_days - 1)
            if entry.exit_date and entry.exit_date > invoiced_until:
                # Bill residual: invoiced_until+1 to exit_date
                create_residual_line_item(entry, invoiced_until + 1, entry.exit_date)
```

**Add indicator to OnDemandInvoiceItem:**
```python
# No new fields needed - can calculate from existing:
# invoiced_until = entry_date + total_days - 1
# is_active_at_invoice = exit_date IS NULL
```

---

## 2. No Double-Billing of Additional Charges

### Problem
Additional charges could be billed in both on-demand invoice AND monthly statement.

### Solution
Exclude charges already billed in another document.

### Implementation

**Monthly statement service** (`_create_service_items`):
```python
charges = AdditionalCharge.objects.filter(
    container_entry__company=company,
    charge_date__gte=month_start,
    charge_date__lte=month_end,
).exclude(
    # Exclude charges already in on-demand invoices
    on_demand_service_items__invoice__status__in=['draft', 'finalized', 'paid']
)
```

**On-demand invoice service** (`create_invoice`):
```python
charges = AdditionalCharge.objects.filter(
    container_entry_id__in=container_entry_ids,
).exclude(
    # Exclude charges already in monthly statements
    statement_service_items__statement__status__in=['draft', 'finalized', 'paid']
)
```

---

## 3. Cancellation Workflow

### 3a. Draft Deletion
Drafts can be **deleted entirely** (hard delete, no trace).

**Implementation:**
- Add `DELETE /api/auth/companies/{slug}/on-demand-invoices/{id}/` endpoint
- Only allowed when `status == 'draft'`
- Hard delete (not soft delete)

### 3b. Finalized Cancellation Audit
Cancelling finalized invoices requires reason and creates audit trail.

**New fields for `OnDemandInvoice`:**
```python
cancelled_at = models.DateTimeField(null=True, blank=True)
cancelled_by = models.ForeignKey(
    "accounts.CustomUser",
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name="cancelled_on_demand_invoices",
)
cancellation_reason = models.TextField(
    blank=True,
    default="",
    help_text="Required when cancelling finalized invoice",
)
```

**Service validation:**
```python
def cancel_invoice(self, invoice, user, reason=""):
    if invoice.status == StatementStatus.DRAFT:
        # Drafts: just delete, no reason needed
        invoice.delete()
        return None

    if invoice.status == StatementStatus.FINALIZED:
        if not reason.strip():
            raise BusinessLogicError(
                "Укажите причину отмены",
                error_code="CANCELLATION_REASON_REQUIRED",
            )
        invoice.status = StatementStatus.CANCELLED
        invoice.cancelled_at = timezone.now()
        invoice.cancelled_by = user
        invoice.cancellation_reason = reason
        invoice.save()
        return invoice

    # PAID cannot be cancelled
    raise BusinessLogicError(...)
```

---

## 4. Payment Tracking

### New Fields for `OnDemandInvoice`
```python
payment_reference = models.CharField(
    max_length=100,
    blank=True,
    default="",
    verbose_name="Референс платежа",
    help_text="Номер банковской транзакции, чека и т.д.",
)
payment_date = models.DateField(
    null=True,
    blank=True,
    verbose_name="Дата платежа",
    help_text="Фактическая дата оплаты (может отличаться от даты отметки)",
)
```

### UI Changes
When clicking "Mark as Paid", show modal with optional fields:
- Payment reference (text input)
- Payment date (date picker, defaults to today)

### API Changes
```python
# POST /on-demand-invoices/{id}/mark-paid/
{
    "payment_reference": "Bank transfer #12345",  // optional
    "payment_date": "2026-02-05"  // optional, defaults to today
}
```

---

## 5. Tax/VAT

**Decision:** Not needed in MTT.

Official tax documentation (счёт-фактура) is handled by 1C accounting system. MTT generates operational/customer-facing invoices only.

---

## Migration Plan

### Database Migration
```python
# Migration: add_cancellation_and_payment_fields

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0010_...'),
    ]

    operations = [
        migrations.AddField(
            model_name='ondemandinvoice',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ondemandinvoice',
            name='cancelled_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=models.SET_NULL,
                related_name='cancelled_on_demand_invoices',
                to='accounts.customuser',
            ),
        ),
        migrations.AddField(
            model_name='ondemandinvoice',
            name='cancellation_reason',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='ondemandinvoice',
            name='payment_reference',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='ondemandinvoice',
            name='payment_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/apps/billing/models.py` | Add new fields to OnDemandInvoice |
| `backend/apps/billing/services/on_demand_invoice_service.py` | Update cancel logic, mark_paid logic, exclude billed charges |
| `backend/apps/billing/services/statement_service.py` | Residual billing logic, exclude billed charges |
| `backend/apps/billing/serializers.py` | Add new fields to serializers |
| `backend/apps/accounts/company_views.py` | Add delete endpoint, update cancel/mark-paid |
| `frontend/src/components/billing/OnDemandInvoices.vue` | Cancel modal with reason, payment modal with fields |
| `frontend/src/components/billing/CurrentCosts.vue` | Show residual indicator if applicable |

---

## Testing Checklist

- [ ] Active container invoiced → stays longer → residual appears in monthly
- [ ] Additional charge in on-demand → excluded from monthly
- [ ] Additional charge in monthly → excluded from on-demand
- [ ] Draft invoice → can be deleted
- [ ] Finalized invoice → cancel requires reason
- [ ] Paid invoice → cannot be cancelled
- [ ] Mark paid → can add reference and date
- [ ] PDF export shows payment reference if present
