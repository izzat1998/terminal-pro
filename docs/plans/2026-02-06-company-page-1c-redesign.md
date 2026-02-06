# Company Page 1C-Style Redesign

**Date:** 2026-02-06
**Status:** Approved

## Overview

Redesign the Company detail page and list page to follow 1C:Enterprise UX patterns:
- Left sidebar navigation instead of horizontal tabs
- Stats bar with key metrics in the header
- Document-centric workflow with status progression for billing documents

## Scope

- **Only** the company detail layout (`CompanyLayout.vue`) and list page (`Companies.vue`)
- No changes to the main app layout (top navbar, global sidebar)
- No backend changes — all data available from existing API

---

## 1. Company Detail Layout (CompanyLayout.vue)

### Header (always visible)

```
[← Компании]                                    [⚙ Действия]

🏢  Company Name
    ● Активна  ·  Создана: 15 марта 2024

┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│💰 Баланс ││💰 Баланс ││📦 На     ││👥        │
│   USD    ││   UZS    ││терминале ││Клиентов  │
│ $12,400  ││ 156M сум ││ 23       ││ 8        │
└──────────┘└──────────┘└──────────┘└──────────┘
```

**Stats cards (4, from existing API):**

| Card | Source field | Clickable |
|------|-------------|-----------|
| Баланс USD | `balance_usd` | No |
| Баланс UZS | `balance_uzs` | No |
| На терминале | `entries_count` | Yes → Контейнеры |
| Клиентов | `customers_count` | Yes → Список клиентов |

- Balance shows red text when negative
- Clickable cards navigate to corresponding sidebar section

### Sidebar (left, ~200px fixed)

```
ОСНОВНОЕ
● Реквизиты        (active = blue left border + light bg)

КЛИЕНТЫ
○ Список
○ Заказы

СКЛАД
○ Контейнеры

РАСЧЁТЫ
○ Текущие
○ Акты
○ Счета

НАСТРОЙКИ
○ Telegram
○ Биллинг
```

- Group labels: gray, uppercase, small font, non-clickable
- Items: clickable, hover highlight, active state with left border accent
- Content area takes remaining width, scrolls independently

### Route Mapping

| Sidebar item | Route path | Component |
|-------------|-----------|-----------|
| Реквизиты | `/companies/:slug` | CompanyInfo.vue |
| Список | `/companies/:slug/users` | CompanyUsers.vue |
| Заказы | `/companies/:slug/orders` | CompanyOrders.vue |
| Контейнеры | `/companies/:slug/containers` | CompanyContainers.vue |
| Текущие | `/companies/:slug/billing/current` | CurrentCosts.vue |
| Акты | `/companies/:slug/billing/statements` | MonthlyStatements.vue |
| Счета | `/companies/:slug/billing/invoices` | OnDemandInvoices.vue |
| Telegram | `/companies/:slug/settings/telegram` | CompanyTelegramSettings.vue |
| Биллинг | `/companies/:slug/settings/billing` | CompanyBillingSettings.vue |

**Default route:** `/companies/:slug` → Реквизиты

---

## 2. Document Status Workflow (Расчёты section)

### Status Progression

**Monthly Statements (Акты):**
```
⚪ Черновик  →  🟡 Проведён  →  🟢 Оплачен
```

**On-Demand Invoices (Счета):**
```
⚪ Черновик  →  🟡 Проведён  →  🟢 Оплачен
                                ↘ 🔴 Отменён
```

### Actions Per Status

| Status | Actions |
|--------|---------|
| ⚪ Черновик | Провести, Удалить, Экспорт |
| 🟡 Проведён | Оплатить, Кредит-нота, Экспорт |
| 🟢 Оплачен | Снять оплату, Экспорт |
| 🔴 Отменён | (read-only) Экспорт |

### Document Journal View

Both Акты and Счета display as document lists with columns:
- №, Период/Дата, Сумма, Статус (color badge), Действия

All actions map to existing backend endpoints:
- `finalize/`, `mark-paid/`, `credit-note/`, `cancel/`
- `export/excel`, `export/pdf`

---

## 3. Companies List Page (Companies.vue)

### Layout

```
Компании                                    [+ Создать]

[🔍 Поиск...]  [Статус: Все ▾]

Всего: 24  ·  Активных: 21  ·  Неактивных: 3

┌───┬──────────────┬────────┬──────┬──────┬────────┬──────┐
│ № │ Компания     │Статус  │Клиен.│Конт. │Баланс  │ Дата │
└───┴──────────────┴────────┴──────┴──────┴────────┴──────┘
```

### Changes from Current

| Feature | Current | New |
|---------|---------|-----|
| Summary stats | None | Stats bar from `/companies/stats/` endpoint |
| Filters | None | Search + Status dropdown |
| Balance | USD + UZS columns | USD primary, UZS on hover |
| Negative balance | No styling | Red text |
| Row click | Goes to `/users` | Goes to Реквизиты (default) |
| Telegram column | Shown | Removed (detail-level info) |
| Actions column | Settings gear | Removed (click row to open) |

---

## 4. Implementation Plan

### Files Changed

| File | Action |
|------|--------|
| `CompanyLayout.vue` | Rewrite — tabs → sidebar + stats header |
| `Companies.vue` | Rework — stats bar, clean columns, row click |
| `router/index.ts` | Add child routes for billing/settings split |
| `MonthlyStatements.vue` | Add status badges + action buttons |
| `OnDemandInvoices.vue` | Add status badges + action buttons |
| `CurrentCosts.vue` | Make standalone route-ready |
| `CompanyBilling.vue` | Delete (no longer needed) |
| `CompanySettings.vue` | Split → CompanyTelegramSettings + CompanyBillingSettings |

### No Backend Changes

All data already available from existing API endpoints.
