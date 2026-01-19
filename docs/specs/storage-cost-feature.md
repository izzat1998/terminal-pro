# Storage Cost Feature Specification

> **Version:** 1.0
> **Date:** January 2025
> **Status:** Approved for Implementation

## 1. Overview

### 1.1 Purpose
Implement a storage cost calculation system for the MTT Container Terminal that accurately calculates charges based on container storage duration, with support for:
- Different rates by container size (20ft/40ft) and status (laden/empty)
- Dual currency pricing (USD and UZS)
- Company-specific special tariffs
- Time-versioned tariffs (rates can change without affecting past periods)
- Free storage days per container entry

### 1.2 Scope
This feature covers:
- ✅ Tariff management (general and company-specific)
- ✅ Storage cost calculation engine
- ✅ Admin interface for tariff management
- ✅ Customer portal cost display
- ✅ API endpoints for cost queries

Out of scope (future phases):
- ❌ Invoice generation
- ❌ Payment tracking
- ❌ Crane operation charges
- ❌ Transport handling fees

---

## 2. Business Rules

### 2.1 Pricing Dimensions

| Dimension | Values | Notes |
|-----------|--------|-------|
| Container Size | `20ft`, `40ft` | Derived from ISO type code |
| Container Status | `laden`, `empty` | From ContainerEntry.status |
| Currency | USD, UZS | Both stored independently |
| Tariff Type | General, Special | Special = per-company |

### 2.2 Core Calculation Rules

| Rule | Description |
|------|-------------|
| **Day Counting** | Calendar days (entry day = day 1) |
| **Tariff Changes** | Split by periods - each period charged at its own rate |
| **Free Days** | Fixed at entry time, do not change if tariff changes |
| **Special Tariff Expiry** | Switch to general tariff from expiry date onwards |
| **Active Containers** | Calculate charges up to current date |
| **Minimum Charge** | If entry and exit same day, count as 1 day |

### 2.3 Free Days Logic

```
Free days are determined ONCE when container enters:
1. Check if company has active special tariff on entry date
2. If yes → use free_days from special tariff
3. If no → use free_days from general tariff
4. This value is LOCKED for entire container stay
5. Free days are consumed first, before any billing begins
```

### 2.4 Tariff Priority

```
When finding applicable tariff for a date:
1. First: Look for company-specific tariff valid on that date
2. Fallback: Use general tariff (company=NULL) valid on that date
3. Error: If no valid tariff found, raise TariffNotFoundError
```

---

## 3. Data Models

### 3.1 Tariff

Represents a pricing version for a specific time period.

```python
class Tariff(TimestampedModel):
    """
    A tariff version representing pricing rules for a time period.

    - company=NULL means this is a general (default) tariff
    - company=X means this is a special tariff for that company
    - Only one tariff can be active per company at any time
    """

    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tariffs',
        help_text="NULL for general tariff, set for company-specific"
    )

    effective_from = models.DateField(
        help_text="Date this tariff becomes active"
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text="Date this tariff ends (NULL = currently active)"
    )

    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.PROTECT,
        related_name='created_tariffs'
    )

    notes = models.TextField(
        blank=True,
        help_text="Reason for creating/changing this tariff"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'effective_from'],
                name='unique_tariff_per_company_date'
            )
        ]
        indexes = [
            models.Index(fields=['company', 'effective_from', 'effective_to']),
            models.Index(fields=['effective_from']),
        ]
```

### 3.2 TariffRate

Holds actual pricing for each size/status combination.

```python
class ContainerSize(models.TextChoices):
    TWENTY_FT = '20ft', '20 футов'
    FORTY_FT = '40ft', '40 футов'


class ContainerStatus(models.TextChoices):
    LADEN = 'laden', 'Груженый'
    EMPTY = 'empty', 'Порожний'


class TariffRate(TimestampedModel):
    """
    Pricing details for a specific container size/status combination.
    Each Tariff should have exactly 4 TariffRate records.
    """

    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.CASCADE,
        related_name='rates'
    )

    container_size = models.CharField(
        max_length=10,
        choices=ContainerSize.choices
    )

    container_status = models.CharField(
        max_length=10,
        choices=ContainerStatus.choices
    )

    daily_rate_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Daily storage rate in USD"
    )

    daily_rate_uzs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Daily storage rate in UZS"
    )

    free_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of free storage days"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tariff', 'container_size', 'container_status'],
                name='unique_rate_per_tariff_size_status'
            )
        ]
```

### 3.3 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌──────────────┐
│   Company   │◄──────│   Tariff    │───────►│  TariffRate  │
│             │  0..* │             │  1:4   │              │
│  - name     │       │  - company  │        │  - size      │
│  - slug     │       │  - eff_from │        │  - status    │
│             │       │  - eff_to   │        │  - rate_usd  │
└─────────────┘       │  - notes    │        │  - rate_uzs  │
                      └─────────────┘        │  - free_days │
                                             └──────────────┘
                             │
                             │ used by
                             ▼
                      ┌──────────────────┐
                      │  ContainerEntry  │
                      │                  │
                      │  - entry_time    │
                      │  - exit_date     │
                      │  - status        │
                      │  - company       │
                      └──────────────────┘
```

---

## 4. Calculation Service

### 4.1 Service Interface

```python
class StorageCostService(BaseService):
    """
    Service for calculating container storage costs.
    """

    def calculate_cost(
        self,
        container_entry: ContainerEntry,
        as_of_date: date = None
    ) -> StorageCostResult:
        """
        Calculate storage cost for a container entry.

        Args:
            container_entry: The container to calculate cost for
            as_of_date: Calculate up to this date (default: today or exit_date)

        Returns:
            StorageCostResult with breakdown
        """
        pass

    def calculate_bulk_costs(
        self,
        container_entries: QuerySet[ContainerEntry]
    ) -> list[StorageCostResult]:
        """
        Calculate costs for multiple containers efficiently.
        """
        pass

    def get_applicable_tariff(
        self,
        company: Company | None,
        target_date: date
    ) -> Tariff:
        """
        Find the tariff applicable for a company on a given date.
        """
        pass
```

### 4.2 Result Data Class

```python
@dataclass
class StorageCostPeriod:
    """A single billing period within the total calculation."""
    start_date: date
    end_date: date
    days: int
    free_days_used: int
    billable_days: int
    tariff_id: int
    tariff_type: str  # 'general' or 'special'
    daily_rate_usd: Decimal
    daily_rate_uzs: Decimal
    amount_usd: Decimal
    amount_uzs: Decimal


@dataclass
class StorageCostResult:
    """Complete storage cost calculation result."""
    container_entry_id: int
    container_number: str
    company_name: str | None

    # Container details
    container_size: str
    container_status: str

    # Dates
    entry_date: date
    end_date: date  # exit_date or calculation date
    is_active: bool  # True if container still in terminal

    # Summary
    total_days: int
    free_days_applied: int
    billable_days: int

    # Totals
    total_usd: Decimal
    total_uzs: Decimal

    # Breakdown by period
    periods: list[StorageCostPeriod]

    # Metadata
    calculated_at: datetime
```

### 4.3 Calculation Algorithm (Pseudocode)

```python
def calculate_cost(container_entry, as_of_date=None):
    # 1. Determine calculation dates
    entry_date = container_entry.entry_time.date()
    end_date = as_of_date or container_entry.exit_date or today()
    is_active = container_entry.exit_date is None

    # 2. Determine container properties
    size = derive_size_from_iso_type(container_entry.container.iso_type)
    status = map_status(container_entry.status)  # LADEN→laden, EMPTY→empty
    company = container_entry.company

    # 3. Initialize tracking variables
    periods = []
    total_usd = Decimal('0')
    total_uzs = Decimal('0')
    free_days_remaining = None  # Set from first tariff
    current_date = entry_date

    # 4. Process each tariff period
    while current_date <= end_date:
        # Find applicable tariff
        tariff = get_applicable_tariff(company, current_date)
        rate = tariff.rates.get(
            container_size=size,
            container_status=status
        )

        # Set free days on first iteration (locked at entry)
        if free_days_remaining is None:
            free_days_remaining = rate.free_days

        # Calculate period boundaries
        period_end = min(
            end_date,
            tariff.effective_to or end_date,
            get_next_tariff_start(company, current_date) - 1 day
        )

        days_in_period = (period_end - current_date).days + 1

        # Apply free days
        free_days_used = min(free_days_remaining, days_in_period)
        free_days_remaining -= free_days_used
        billable_days = days_in_period - free_days_used

        # Calculate amounts
        amount_usd = billable_days * rate.daily_rate_usd
        amount_uzs = billable_days * rate.daily_rate_uzs

        # Record period
        periods.append(StorageCostPeriod(
            start_date=current_date,
            end_date=period_end,
            days=days_in_period,
            free_days_used=free_days_used,
            billable_days=billable_days,
            tariff_id=tariff.id,
            tariff_type='special' if tariff.company else 'general',
            daily_rate_usd=rate.daily_rate_usd,
            daily_rate_uzs=rate.daily_rate_uzs,
            amount_usd=amount_usd,
            amount_uzs=amount_uzs,
        ))

        total_usd += amount_usd
        total_uzs += amount_uzs

        # Move to next period
        current_date = period_end + 1 day

    # 5. Build and return result
    return StorageCostResult(
        container_entry_id=container_entry.id,
        container_number=container_entry.container.container_number,
        company_name=company.name if company else None,
        container_size=size,
        container_status=status,
        entry_date=entry_date,
        end_date=end_date,
        is_active=is_active,
        total_days=(end_date - entry_date).days + 1,
        free_days_applied=initial_free_days - free_days_remaining,
        billable_days=sum(p.billable_days for p in periods),
        total_usd=total_usd,
        total_uzs=total_uzs,
        periods=periods,
        calculated_at=now(),
    )
```

### 4.4 Container Size Derivation

```python
def derive_size_from_iso_type(iso_type: str) -> ContainerSize:
    """
    Derive container size from ISO type code.

    ISO codes starting with:
    - 2 (20, 22, 25, etc.) → 20ft
    - 4 (40, 42, 45, etc.) → 40ft
    """
    if iso_type and iso_type[0] == '2':
        return ContainerSize.TWENTY_FT
    elif iso_type and iso_type[0] == '4':
        return ContainerSize.FORTY_FT
    else:
        # Default to 20ft if unknown
        return ContainerSize.TWENTY_FT
```

---

## 5. API Endpoints

### 5.1 Tariff Management (Admin)

#### List/Create Tariffs

```
GET  /api/tariffs/
POST /api/tariffs/

Query params:
  - company_id: Filter by company (omit for general tariffs)
  - active: true = only currently active tariffs

Request body (POST):
{
  "company": null,  // null for general, company_id for special
  "effective_from": "2025-01-15",
  "effective_to": null,
  "notes": "Annual rate adjustment",
  "rates": [
    {
      "container_size": "20ft",
      "container_status": "laden",
      "daily_rate_usd": "10.00",
      "daily_rate_uzs": "125000.00",
      "free_days": 5
    },
    // ... 3 more for other combinations
  ]
}

Response:
{
  "success": true,
  "data": {
    "id": 1,
    "company": null,
    "company_name": null,
    "effective_from": "2025-01-15",
    "effective_to": null,
    "is_active": true,
    "notes": "Annual rate adjustment",
    "rates": [...],
    "created_by": "admin",
    "created_at": "2025-01-15T10:00:00Z"
  }
}
```

#### Get/Update Tariff

```
GET    /api/tariffs/{id}/
PATCH  /api/tariffs/{id}/
DELETE /api/tariffs/{id}/

Note: DELETE only allowed if tariff has no associated calculations
Note: PATCH can only update effective_to and notes
```

#### List Company Special Tariffs

```
GET /api/companies/{company_id}/tariffs/

Response:
{
  "success": true,
  "data": [
    {
      "id": 5,
      "effective_from": "2025-01-01",
      "effective_to": "2025-06-30",
      "is_active": true,
      "rates": [...]
    }
  ]
}
```

### 5.2 Storage Cost Calculation

#### Calculate for Single Container

```
GET /api/container-entries/{id}/storage-cost/

Query params:
  - as_of_date: Calculate up to this date (default: today or exit_date)

Response:
{
  "success": true,
  "data": {
    "container_entry_id": 123,
    "container_number": "MSKU1234567",
    "company_name": "ABC Logistics",
    "container_size": "40ft",
    "container_status": "laden",
    "entry_date": "2025-01-05",
    "end_date": "2025-02-10",
    "is_active": false,
    "total_days": 37,
    "free_days_applied": 5,
    "billable_days": 32,
    "total_usd": "395.00",
    "total_uzs": "4937500.00",
    "periods": [
      {
        "start_date": "2025-01-05",
        "end_date": "2025-01-14",
        "days": 10,
        "free_days_used": 5,
        "billable_days": 5,
        "tariff_type": "special",
        "daily_rate_usd": "8.00",
        "daily_rate_uzs": "100000.00",
        "amount_usd": "40.00",
        "amount_uzs": "500000.00"
      },
      // ... more periods
    ],
    "calculated_at": "2025-02-10T14:30:00Z"
  }
}
```

#### Bulk Calculate (for reports)

```
POST /api/storage-costs/calculate/

Request body:
{
  "container_entry_ids": [123, 456, 789],
  // OR
  "filters": {
    "company_id": 5,
    "status": "active",  // active, exited, all
    "entry_date_from": "2025-01-01",
    "entry_date_to": "2025-01-31"
  },
  "as_of_date": "2025-01-31"
}

Response:
{
  "success": true,
  "data": {
    "results": [...],
    "summary": {
      "total_containers": 15,
      "total_usd": "5420.00",
      "total_uzs": "67750000.00",
      "total_billable_days": 542
    }
  }
}
```

### 5.3 Customer Portal Endpoints

#### My Storage Costs

```
GET /api/customer/storage-costs/

Response (filtered to customer's company automatically):
{
  "success": true,
  "data": {
    "active_containers": [
      {
        "container_number": "MSKU1234567",
        "entry_date": "2025-01-10",
        "days_stored": 5,
        "current_cost_usd": "25.00",
        "current_cost_uzs": "312500.00"
      }
    ],
    "summary": {
      "total_active": 3,
      "total_current_cost_usd": "150.00",
      "total_current_cost_uzs": "1875000.00"
    }
  }
}
```

---

## 6. Admin UI Components

### 6.1 Tariff Management Page

**Location:** `/admin/tariffs`

**Features:**
- View all tariffs (tabbed: General | Company-specific)
- Create new tariff version
- End current tariff (set effective_to)
- View tariff history

**Tariff Table Columns:**
| Column | Description |
|--------|-------------|
| Company | "General" or company name |
| Effective From | Start date |
| Effective To | End date or "Active" badge |
| 20ft Laden | Rate USD / UZS |
| 20ft Empty | Rate USD / UZS |
| 40ft Laden | Rate USD / UZS |
| 40ft Empty | Rate USD / UZS |
| Free Days | Days per size/status |
| Actions | Edit, End, View History |

### 6.2 Create/Edit Tariff Form

```
┌─────────────────────────────────────────────────────────────┐
│  New Tariff                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Tariff Type:  ○ General   ○ Company-specific               │
│                                                              │
│  Company: [Dropdown - only if company-specific]              │
│                                                              │
│  Effective From: [Date picker] ────────────────────────────  │
│  Effective To:   [Date picker] (optional)                    │
│                                                              │
│  Notes: [Text area for reason]                               │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Rates                                                       │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  ┌──────────┬────────────┬────────────┬───────────────────┐ │
│  │          │ USD/day    │ UZS/day    │ Free Days         │ │
│  ├──────────┼────────────┼────────────┼───────────────────┤ │
│  │ 20ft     │            │            │                   │ │
│  │ Laden    │ [_______]  │ [________] │ [___]             │ │
│  ├──────────┼────────────┼────────────┼───────────────────┤ │
│  │ 20ft     │            │            │                   │ │
│  │ Empty    │ [_______]  │ [________] │ [___]             │ │
│  ├──────────┼────────────┼────────────┼───────────────────┤ │
│  │ 40ft     │            │            │                   │ │
│  │ Laden    │ [_______]  │ [________] │ [___]             │ │
│  ├──────────┼────────────┼────────────┼───────────────────┤ │
│  │ 40ft     │            │            │                   │ │
│  │ Empty    │ [_______]  │ [________] │ [___]             │ │
│  └──────────┴────────────┴────────────┴───────────────────┘ │
│                                                              │
│  [Cancel]                                    [Save Tariff]   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Container Entry Cost View

**Enhancement to existing ContainerEntry detail page:**

```
┌─────────────────────────────────────────────────────────────┐
│  Container: MSKU1234567                                      │
│  ─────────────────────────────────────────────────────────  │
│  ... existing container details ...                          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  💰 Storage Cost                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  Entry Date:    January 5, 2025                              │
│  Exit Date:     February 10, 2025                            │
│  Total Days:    37 days                                      │
│  Free Days:     5 days                                       │
│  Billable:      32 days                                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Total Cost                                              ││
│  │                                                         ││
│  │   $395.00 USD                                           ││
│  │   4,937,500 сум                                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  📊 Cost Breakdown by Period                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Jan 5-14 (Special) │ 10 days │ 5 free │ $40.00         ││
│  │ Jan 15-19 (Special)│  5 days │ 0 free │ $40.00         ││
│  │ Jan 20-24 (General)│  5 days │ 0 free │ $60.00         ││
│  │ Jan 25-Feb 10      │ 17 days │ 0 free │ $255.00        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Customer Portal UI

### 7.1 Storage Costs Summary Card

**Location:** Customer dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  📦 Storage Charges                                          │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  Active Containers: 3                                        │
│                                                              │
│  Current Balance:                                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                         ││
│  │   $150.00 USD                                           ││
│  │   1,875,000 сум                                         ││
│  │                                                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  [View Details →]                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Storage Cost Detail Page

**Location:** `/customer/storage-costs`

```
┌─────────────────────────────────────────────────────────────┐
│  My Storage Costs                                            │
│  ═══════════════════════════════════════════════════════════│
│                                                              │
│  [Active ▼]  [All Containers ▼]  [This Month ▼]             │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Container     │ Entry   │ Days │ Free │ Cost USD │ UZS  ││
│  ├───────────────┼─────────┼──────┼──────┼──────────┼──────┤│
│  │ MSKU1234567   │ Jan 10  │  5   │  3   │  $20.00  │250K  ││
│  │ TCLU9876543   │ Jan 8   │  7   │  0   │  $70.00  │875K  ││
│  │ MRKU5555555   │ Jan 12  │  3   │  3   │  $0.00   │  0   ││
│  └───────────────┴─────────┴──────┴──────┴──────────┴──────┘│
│                                                              │
│  Total: $90.00 USD / 1,125,000 сум                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Validation Rules

### 8.1 Tariff Validation

| Rule | Description |
|------|-------------|
| **No overlapping tariffs** | For same company, date ranges cannot overlap |
| **General tariff required** | System must always have an active general tariff |
| **Future dating only** | New tariff effective_from must be ≥ today |
| **All rates required** | All 4 size/status combinations must be provided |
| **Non-negative rates** | All rates and free_days must be ≥ 0 |
| **Consistent currencies** | Both USD and UZS must be provided for all rates |

### 8.2 Calculation Validation

| Rule | Description |
|------|-------------|
| **Valid container entry** | Entry must exist and have valid entry_time |
| **Valid ISO type** | Must be able to derive size from ISO type |
| **Tariff must exist** | Error if no valid tariff found for any period |

---

## 9. Error Handling

### 9.1 Custom Exceptions

```python
class TariffNotFoundError(BusinessLogicError):
    """No valid tariff found for the given date and company."""
    code = "TARIFF_NOT_FOUND"
    message = "Тариф не найден для указанной даты"


class TariffOverlapError(BusinessLogicError):
    """Tariff date range overlaps with existing tariff."""
    code = "TARIFF_OVERLAP"
    message = "Даты тарифа пересекаются с существующим тарифом"


class InvalidContainerSizeError(BusinessLogicError):
    """Cannot determine container size from ISO type."""
    code = "INVALID_CONTAINER_SIZE"
    message = "Невозможно определить размер контейнера"
```

---

## 10. Database Migrations

### 10.1 Migration Plan

```
Migration 1: Create Tariff model
Migration 2: Create TariffRate model
Migration 3: Add indexes for performance
Migration 4: Create initial general tariff (data migration)
```

### 10.2 Initial Data

The system requires at least one general tariff to function. A data migration should create a default tariff with placeholder rates that admin must update.

---

## 11. Testing Requirements

### 11.1 Unit Tests

- [ ] `test_derive_size_from_iso_type` - All ISO type variations
- [ ] `test_calculate_cost_single_period` - Simple case
- [ ] `test_calculate_cost_multiple_periods` - Tariff change mid-stay
- [ ] `test_free_days_locked_at_entry` - Free days don't change
- [ ] `test_special_tariff_expiry` - Fallback to general
- [ ] `test_calendar_day_counting` - Edge cases
- [ ] `test_active_container_calculation` - Up to today
- [ ] `test_bulk_calculation` - Multiple containers

### 11.2 Integration Tests

- [ ] API endpoint tests for all endpoints
- [ ] Permission tests (admin vs customer access)
- [ ] Tariff CRUD operations
- [ ] Cost calculation accuracy

---

## 12. Implementation Phases

### Phase 1: Backend Foundation
1. Create models and migrations
2. Implement StorageCostService
3. Create API endpoints
4. Write unit tests

### Phase 2: Admin Interface
1. Tariff management pages
2. Cost display on container detail
3. Bulk cost report

### Phase 3: Customer Portal
1. Storage cost summary card
2. Cost detail page
3. Cost column in container list

### Phase 4: Polish & Optimization
1. Performance optimization for bulk calculations
2. Caching strategy
3. Export functionality (Excel/PDF)

---

## 13. Appendix

### A. Example Tariff Data

**General Tariff (Default):**
| Size | Status | USD/day | UZS/day | Free Days |
|------|--------|---------|---------|-----------|
| 20ft | Laden  | $10.00  | 125,000 | 5 |
| 20ft | Empty  | $8.00   | 100,000 | 5 |
| 40ft | Laden  | $18.00  | 225,000 | 5 |
| 40ft | Empty  | $15.00  | 187,500 | 5 |

**Special Tariff (ABC Logistics):**
| Size | Status | USD/day | UZS/day | Free Days |
|------|--------|---------|---------|-----------|
| 20ft | Laden  | $8.00   | 100,000 | 7 |
| 20ft | Empty  | $6.00   | 75,000  | 7 |
| 40ft | Laden  | $14.00  | 175,000 | 7 |
| 40ft | Empty  | $12.00  | 150,000 | 7 |

### B. ISO Type Size Mapping

| First Digit | Size | Examples |
|-------------|------|----------|
| 2           | 20ft | 22G1, 22K2, 25G1 |
| 4           | 40ft | 42G1, 45G1, 40F |
| L           | 45ft | L5G1 (treat as 40ft) |

---

*End of Specification*
