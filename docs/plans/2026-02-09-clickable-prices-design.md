# Clickable Price Cells in Current Costs Table

**Date:** 2026-02-09
**Status:** Design approved (revised after codebase review)

## Summary

Make all three price columns in the CurrentCosts billing table interactive:

| Column | Click action | Modal |
|--------|-------------|-------|
| Итого USD | Period breakdown + tariff details | Existing `StorageCostModal` |
| Не выставлено | Same period breakdown | Existing `StorageCostModal` |
| Выставлено | Invoice/statement list + act HTML preview | **New** `BilledDetailModal` |

Both admin and customer users can access the detail views.

## Backend: New Endpoint

### `GET /api/billing/container-entry/{entry_id}/billing-detail/`

Returns all billing documents (monthly statements + on-demand invoices) that include the given container entry.

**Admin URL:** `/api/billing/container-entry/{entry_id}/billing-detail/`
**Customer URL:** `/api/customer/container-entry/{entry_id}/billing-detail/`

**Response:**
```json
{
  "success": true,
  "data": {
    "container_entry_id": 123,
    "container_number": "HDMU6565958",
    "total_billed_usd": "350.00",
    "total_billed_uzs": "4375000",
    "total_paid_usd": "150.00",
    "total_paid_uzs": "1875000",
    "documents": [
      {
        "type": "statement",
        "id": 12,
        "number": "№2026-01-001",
        "period": "Январь 2026",
        "status": "paid",
        "amount_usd": "150.00",
        "amount_uzs": "1875000",
        "created_at": "2026-02-01",
        "act_preview_url": "/api/billing/companies/slug/statements/2026/1/export/act-html-preview/"
      },
      {
        "type": "on_demand_invoice",
        "id": 3,
        "number": "OD-2026-003",
        "period": null,
        "status": "draft",
        "amount_usd": "200.00",
        "amount_uzs": "2500000",
        "created_at": "2026-02-05",
        "act_preview_url": null
      }
    ]
  }
}
```

### Implementation

- Query `StatementLineItem` for the entry → join to `MonthlyStatement` for status, invoice_number, year/month
- Query `OnDemandInvoiceItem` for the entry → join to `OnDemandInvoice` for status, invoice_number
- Build `act_preview_url` from the statement's company slug + year/month (**only for monthly statements**)
- On-demand invoices: `act_preview_url` = `null` (no act preview exists yet — future task)
- Customer endpoint validates company ownership via `_get_customer_company()`

## Frontend: Changes

### 1. Make price cells clickable in `CurrentCosts.vue`

- **Итого USD** + **Не выставлено**: `@click="showCostDetails(record)"` — opens existing `StorageCostModal`
- **Выставлено**: `@click="showBilledDetails(record)"` — opens new `BilledDetailModal`
- Add `.clickable-amount` CSS class with cursor pointer + hover underline

### 2. New `BilledDetailModal.vue` component

**Layout:**
1. Header: container number tag + "Детализация выставленных сумм"
2. Summary bar: total billed / paid (green) / unpaid (orange)
3. Document table: type, number, period, amount, status, "Акт" button
4. Act preview area: iframe with `srcdoc` showing fetched act HTML

**Act preview:**
- Fetch HTML from `act_preview_url` via authenticated HTTP call
- Render in `<iframe srcdoc="">` to isolate styles from the app
- **Only available for monthly statements** — on-demand invoices show data in the table but "Акт" button is disabled with tooltip "Предпросмотр акта недоступен для разовых счетов"

### 3. Remove eye icon action (optional)

Since Итого USD is now clickable and opens the same modal, the eye icon button becomes redundant. Can be removed to simplify the UI.

## Known Limitations

| Limitation | Future fix |
|-----------|------------|
| No act preview for on-demand invoices | Adapt `_render_act_html_preview()` and `StatementExportService` for on-demand invoices |
| Export service methods are statement-specific | `_group_line_items()` / `_group_service_items()` need on-demand variants |

## Files to Change

| File | Change |
|------|--------|
| `backend/apps/billing/views.py` | Add `ContainerBillingDetailView` |
| `backend/apps/billing/urls.py` | Register new endpoint |
| `backend/apps/customer_portal/urls.py` | Register customer endpoint |
| `frontend/src/components/billing/BilledDetailModal.vue` | **New** — modal component |
| `frontend/src/components/billing/CurrentCosts.vue` | Make cells clickable, import modal |
