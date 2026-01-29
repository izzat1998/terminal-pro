# Billing Lifecycle & Statement Redesign

**Date:** 2026-01-27
**Status:** Approved

## Overview

Redesign the billing system from simple on-demand statement generation to a full accounting lifecycle with draft→finalized→paid workflow, invoice numbering, credit notes, and unified storage + services billing.

## Section 1: Statement Lifecycle & Document Model

Monthly statements follow a **draft → finalized → paid** lifecycle with credit notes for corrections.

**Statuses:**
- `draft` — Auto-generated on 1st of next month. Admin reviews and adjusts before finalizing.
- `finalized` — Admin confirms. Invoice number assigned (e.g., `MTT-2026-0042`). Amounts locked.
- `paid` — Admin marks as paid. Records who and when.
- `cancelled` — Only when a credit note fully reverses the statement.

**Invoice numbering:**
- Format: `MTT-{YYYY}-{NNNN}` — sequential per year, never reused.
- Assigned only on finalization, not on draft creation.
- Credit notes: `MTT-CR-{YYYY}-{NNNN}` — separate sequence.

**Credit notes:**
- Special statement with `statement_type = 'credit_note'` referencing `original_statement`.
- Contains negative line items showing the difference.
- Original statement remains untouched (audit trail preserved).

**New model fields on MonthlyStatement:**
- `status`: draft / finalized / paid / cancelled
- `statement_type`: invoice / credit_note
- `invoice_number`: unique, assigned on finalization
- `original_statement`: FK to self (for credit notes)
- `finalized_at`, `finalized_by`: audit trail

## Section 2: Statement Content — Unified Storage + Services

Each statement contains two types of line items in a single document.

**Storage line items** (existing `StatementLineItem`):
- One row per container entry.
- Container number, size, status, period, free days, billable days, daily rate, amount.

**Service line items** (from `AdditionalCharge`):
- New model `StatementServiceItem` linked to statement.
- One row per additional charge where `charge_date` falls within the statement month.
- Container number, service description, charge date, amount USD/UZS.

**Statement totals:**
- `total_storage_usd` / `total_storage_uzs` — sum of storage line items
- `total_services_usd` / `total_services_uzs` — sum of additional charges
- `total_usd` / `total_uzs` — grand total (storage + services)
- `total_containers`, `total_billable_days` — storage only

**Pending section** (exit_month billing):
- Containers on terminal that haven't exited.
- Estimated cost so far (informational, not in totals).
- Stored as `pending_containers_data` (JSON snapshot at generation time).

**Charge matching:** By `charge_date` — charge dated Jan 15 → January statement.

## Section 3: Auto-Generation & Backend Changes

**Auto-generation via management command + cron:**
- `generate_monthly_statements` runs on 1st of each month (`0 2 1 * *`).
- Finds all companies with container activity in previous month.
- Creates draft statements. Idempotent (skips existing drafts).

**Statement generation changes:**
- Pulls `AdditionalCharge` records for the month → creates `StatementServiceItem` entries.
- Calculates pending container snapshots for exit_month billing.
- Invoice numbers assigned only in `finalize_statement()`.

**New service methods:**
- `finalize_statement(statement, user)` — locks statement, assigns invoice number.
- `create_credit_note(original, user, adjustments)` — creates credit note.
- `generate_all_drafts(year, month)` — bulk draft generation.
- `get_next_invoice_number(year)` — atomic sequential number.

**New API endpoints:**
- `POST .../statements/{id}/finalize/`
- `POST .../statements/{id}/credit-note/`
- `POST /api/billing/generate-all-drafts/`

**Key rule:** Finalized statements are immutable. Corrections only via credit notes.

## Section 4: Frontend & Export Changes

**Master table:**
- Status column: Черновик (blue), Выставлен (green), Оплачен (gold), Отменён (red).
- Invoice number column (finalized/paid only).
- Admin actions by status:
  - Draft → Утвердить (finalize), Пересчитать (regenerate)
  - Finalized → Отметить оплату, Корректировка (credit note)
  - Paid → Корректировка only
  - Cancelled → no actions
- Credit notes as child rows under original statement.

**Expanded detail:**
- Two sections with sub-totals: Хранение (storage) + Услуги (services).
- Pending containers section (grey, informational).
- Grand total row.

**Export format:**
- Header: invoice number, company, period, date.
- Section 1: Storage costs table.
- Section 2: Additional services table.
- Sub-totals per section, grand total.
- "Черновик" watermark if not finalized.

**Customer portal:** Read-only, no admin actions, pending section visible.

## Implementation Tasks

1. **Task #1:** Update MonthlyStatement model with lifecycle fields + StatementServiceItem model
2. **Task #2:** Update statement service with lifecycle methods (blocked by #1)
3. **Task #3:** Add API endpoints and management command (blocked by #2)
4. **Task #4:** Update frontend for new billing lifecycle (blocked by #3)
