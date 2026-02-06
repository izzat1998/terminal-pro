# On-Demand Invoicing Design

## Problem

Customers sometimes need an invoice immediately for specific exited containers, rather than waiting for the end-of-month billing cycle. The financial specialist needs a fast way to generate these invoices.

## Constraints

- Only exited containers can be invoiced (costs are final)
- Containers included in an on-demand invoice are excluded from the monthly statement (no double-billing)
- Cancelling an on-demand invoice releases containers back to the monthly billing pool
- On-demand invoices are distinct from monthly statements (own model, own numbering)

## Data Model

### OnDemandInvoice

| Field | Type | Description |
|-------|------|-------------|
| company | FK → Company | Company being invoiced |
| invoice_number | CharField, unique, nullable | Assigned on finalization (e.g. OD-2026-0001) |
| status | CharField | draft / finalized / paid / cancelled |
| total_usd | DecimalField | Sum of all line items (USD) |
| total_uzs | DecimalField | Sum of all line items (UZS) |
| notes | TextField, nullable | Reason for early invoicing |
| created_by | FK → User | Specialist who created |
| finalized_at | DateTimeField, nullable | When finalized |
| finalized_by | FK → User, nullable | Who finalized |
| paid_at | DateTimeField, nullable | When marked paid |
| paid_marked_by | FK → User, nullable | Who marked paid |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

### OnDemandInvoiceItem

| Field | Type | Description |
|-------|------|-------------|
| invoice | FK → OnDemandInvoice | Parent invoice |
| container_entry | FK → ContainerEntry | Source entry |
| container_number | CharField | Snapshot |
| container_size | CharField | 20ft / 40ft |
| container_status | CharField | laden / empty |
| entry_date | DateField | Snapshot |
| exit_date | DateField | Snapshot |
| total_days | PositiveIntegerField | Total storage days |
| free_days | PositiveIntegerField | Free days applied |
| billable_days | PositiveIntegerField | Billable days |
| daily_rate_usd | DecimalField | Rate used |
| daily_rate_uzs | DecimalField | Rate used |
| amount_usd | DecimalField | Line total |
| amount_uzs | DecimalField | Line total |

## Service Logic

### OnDemandInvoiceService

Location: `apps/billing/services/on_demand_invoice_service.py`

**create_invoice(company, container_entry_ids, user, notes=None)**
1. Validate all entries belong to this company
2. Validate all entries have exited (exit_date is not None)
3. Validate none already included in another on-demand invoice (status != cancelled)
4. Calculate costs via existing StorageCostService
5. Create OnDemandInvoice + OnDemandInvoiceItems with cost snapshots
6. Return invoice in draft status

**finalize_invoice(invoice, user)**
- Assign invoice_number OD-{year}-{sequential}
- Set status to finalized, record finalized_at/finalized_by

**mark_paid(invoice, user)**
- Toggle between finalized and paid status

**cancel_invoice(invoice, user)**
- Set status to cancelled
- Containers return to monthly billing pool

### Monthly Statement Exclusion

In `MonthlyStatementService`, when generating a statement, exclude container entries that have an on-demand invoice item with non-cancelled status:

```python
entries = entries.exclude(
    on_demand_items__invoice__status__in=['draft', 'finalized', 'paid']
)
```

## API Endpoints

All under `/api/auth/companies/{slug}/`:

| Method | Path | Description |
|--------|------|-------------|
| POST | on-demand-invoices/ | Create draft invoice |
| GET | on-demand-invoices/ | List company invoices |
| GET | on-demand-invoices/{id}/ | Invoice detail with items |
| POST | on-demand-invoices/{id}/finalize/ | Finalize and assign number |
| POST | on-demand-invoices/{id}/mark-paid/ | Toggle payment status |
| POST | on-demand-invoices/{id}/cancel/ | Cancel, release containers |
| GET | on-demand-invoices/{id}/export/excel/ | Excel download |
| GET | on-demand-invoices/{id}/export/pdf/ | PDF download |

### Create Request Body

```json
{
  "container_entry_ids": [1, 2, 3],
  "notes": "По запросу клиента"
}
```

### Validation Errors

- Container still on terminal: "Контейнер XXXX ещё на территории терминала"
- Already invoiced: "Контейнер XXXX уже включён в счёт OD-2026-0001"
- Wrong company: "Контейнер XXXX не принадлежит данной компании"

## UI Design

### Location

Company → Billing tab → Extended with checkboxes on CurrentCosts + new "Разовые счета" tab.

### CurrentCosts Enhancement

- Add checkboxes to exited containers (not already invoiced)
- Containers still on terminal: checkbox disabled
- Already invoiced containers: hidden or marked
- Floating summary bar: selected count + total USD/UZS
- "Выставить разовый счёт" button → confirmation modal with optional notes

### New Tab: Разовые счета

Table columns:
- Invoice number (OD-2026-XXXX)
- Date created
- Container count
- Total USD / UZS
- Status (tag: Черновик / Утверждён / Оплачен / Отменён)

Row actions: Finalize, Toggle payment, Cancel, Export Excel, Export PDF.

Expandable rows show line items (same pattern as MonthlyStatements).
