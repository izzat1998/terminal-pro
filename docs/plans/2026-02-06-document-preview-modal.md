# Document Preview Modal Design

**Date:** 2026-02-06
**Status:** Implemented

## Overview

Added document preview functionality to billing statements. Clicking any export button (Excel, PDF, Счёт-фактура) opens a tabbed modal with a PDF preview before downloading.

## Architecture

### Frontend
- **`DocumentPreviewModal.vue`** — reusable modal with 3 tabs
  - Lazy-loads PDF blobs per tab (no upfront fetch of all 3)
  - Caches blobs per tab (switching tabs reuses cached PDF)
  - Excel & PDF tabs share the same blob (both preview via PDF endpoint)
  - Footer: "Скачать" downloads the native format, "Закрыть" dismisses
  - Width: 90vw max 1200px, iframe: 70vh
  - Cleanup: `URL.revokeObjectURL()` on close and unmount

### Backend
- **`export_to_schet_factura_pdf()`** — new method on `StatementExportService`
  - Reuses `_group_line_items()` and `_group_service_items()` from Excel version
  - Renders `schet_factura_pdf.html` via WeasyPrint
  - A4 landscape, same 2-part layout as Excel (АКТ header + detail table)
- **`act-preview/` endpoints** — returns PDF with `Content-Disposition: inline`

### Tab → Endpoint Mapping

| Tab | Preview endpoint | Download endpoint |
|-----|-----------------|-------------------|
| Детализация Excel | `/export/pdf/` | `/export/excel/` |
| Детализация PDF | `/export/pdf/` | `/export/pdf/` |
| Счёт-фактура | `/export/act-preview/` | `/export/act/` |

## Files Changed

| File | Change |
|------|--------|
| `backend/templates/billing/schet_factura_pdf.html` | New HTML template |
| `backend/apps/billing/services/export_service.py` | Added `export_to_schet_factura_pdf()` |
| `backend/apps/billing/views.py` | Added `*ActPreviewView` classes |
| `backend/apps/billing/urls.py` | Added `act-preview/` URL |
| `backend/apps/customer_portal/urls.py` | Added `act-preview/` URL |
| `backend/apps/accounts/company_views.py` | Added `billing_export_act_preview` action |
| `frontend/src/components/billing/DocumentPreviewModal.vue` | New component |
| `frontend/src/components/billing/MonthlyStatements.vue` | Replaced direct download with modal |
