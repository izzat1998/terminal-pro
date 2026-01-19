# Customer Billing & Monthly Statements Design

**Date:** 2026-01-19
**Status:** Approved
**Author:** Brainstorming session

## Overview

Transform the customer "Storage Costs" page into a comprehensive "Billing" page with two tabs:
1. **Current Costs** — Real-time storage cost calculations (existing functionality)
2. **Monthly Statements** — Persistent monthly billing statements with export capabilities

### Goals
- **Billing transparency** — Customers see what they owe per month
- **Historical reference** — Saved statements for past months
- **Export flexibility** — Both Excel and PDF downloads

### Non-Goals
- Formal invoicing with legal compliance
- Payment tracking / AR workflow
- Automated email notifications (future scope)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Statement generation | Hybrid (on-demand + cached) | Always accurate, but saved for reference |
| Multi-month containers | Split billing (configurable) | Per-company setting, can also use exit-month |
| Detail level | Detailed | Full breakdown with daily rates |
| Export formats | Excel + PDF | Accounting flexibility |
| Navigation | Tabbed "Billing" page | Replaces Storage Costs, cleaner UX |

---

## Data Model

### 1. Company Enhancement

Add billing method configuration to existing Company model:

```python
# apps/accounts/models.py - Add to Company model

class BillingMethod(models.TextChoices):
    SPLIT = 'split', 'Раздельный расчёт'
    EXIT_MONTH = 'exit_month', 'По месяцу выхода'

# Add field to Company:
billing_method = models.CharField(
    max_length=20,
    choices=BillingMethod.choices,
    default=BillingMethod.SPLIT,
    verbose_name='Метод расчёта'
)
```

### 2. MonthlyStatement Model

```python
# apps/billing/models.py

class MonthlyStatement(TimestampedModel):
    """Persisted monthly billing statement for a company."""

    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='statements'
    )
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    billing_method = models.CharField(
        max_length=20,
        choices=BillingMethod.choices,
        help_text='Snapshot of billing method used at generation time'
    )

    # Cached totals
    total_containers = models.PositiveIntegerField(default=0)
    total_billable_days = models.PositiveIntegerField(default=0)
    total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_uzs = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        unique_together = ['company', 'year', 'month']
        ordering = ['-year', '-month']
        verbose_name = 'Monthly Statement'
        verbose_name_plural = 'Monthly Statements'

    def __str__(self):
        return f"{self.company.name} - {self.month:02d}/{self.year}"

    @property
    def month_name(self) -> str:
        """Return Russian month name."""
        months = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        return months[self.month - 1]
```

### 3. StatementLineItem Model

```python
# apps/billing/models.py

class StatementLineItem(TimestampedModel):
    """Individual container cost entry within a statement."""

    statement = models.ForeignKey(
        MonthlyStatement,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    container_entry = models.ForeignKey(
        'terminal_operations.ContainerEntry',
        on_delete=models.SET_NULL,
        null=True,
        help_text='Reference to original entry (may be null if deleted)'
    )

    # Snapshot data (won't change if container data updates)
    container_number = models.CharField(max_length=20)
    container_size = models.CharField(
        max_length=10,
        choices=ContainerSize.choices
    )
    container_status = models.CharField(
        max_length=10,
        choices=ContainerBillingStatus.choices
    )

    # Period for this statement (may be subset of total stay)
    period_start = models.DateField()
    period_end = models.DateField()
    is_still_on_terminal = models.BooleanField(default=False)

    # Day breakdown
    total_days = models.PositiveIntegerField()
    free_days = models.PositiveIntegerField()
    billable_days = models.PositiveIntegerField()

    # Rates used
    daily_rate_usd = models.DecimalField(max_digits=10, decimal_places=2)
    daily_rate_uzs = models.DecimalField(max_digits=12, decimal_places=2)

    # Calculated amounts
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    amount_uzs = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        ordering = ['container_number']

    def __str__(self):
        return f"{self.container_number} ({self.statement})"
```

---

## Service Layer

### MonthlyStatementService

Location: `apps/billing/services/statement_service.py`

```python
class MonthlyStatementService:
    """Generates and manages monthly billing statements."""

    def __init__(self):
        self.storage_cost_service = StorageCostService()

    def get_or_generate_statement(
        self,
        company: Company,
        year: int,
        month: int,
        regenerate: bool = False,
        user: CustomUser = None
    ) -> MonthlyStatement:
        """
        Get existing statement or generate new one.

        Args:
            company: The company to generate statement for
            year: Statement year
            month: Statement month (1-12)
            regenerate: If True, recalculates even if exists
            user: User requesting generation (for audit)

        Returns:
            MonthlyStatement with populated line_items
        """

    def _generate_statement(
        self,
        company: Company,
        year: int,
        month: int,
        user: CustomUser = None
    ) -> MonthlyStatement:
        """
        Core generation logic:
        1. Determine billing method from company.billing_method
        2. Calculate month boundaries (first/last day)
        3. For SPLIT billing:
           - Find containers active during any part of the month
           - Calculate costs only for days within the month
        4. For EXIT_MONTH billing:
           - Find containers that exited during the month
           - Include full stay cost in this statement
        5. Create MonthlyStatement record
        6. Create StatementLineItem for each container
        7. Calculate and save totals
        """

    def _get_containers_for_split_billing(
        self,
        company: Company,
        month_start: date,
        month_end: date
    ) -> QuerySet:
        """
        Find containers active during month:
        - Entry before month end AND
        - (Exit after month start OR still on terminal)
        """

    def _get_containers_for_exit_billing(
        self,
        company: Company,
        month_start: date,
        month_end: date
    ) -> QuerySet:
        """Find containers that exited during the month."""

    def list_statements(
        self,
        company: Company,
        year: int = None
    ) -> QuerySet[MonthlyStatement]:
        """List all statements for a company, optionally filtered by year."""

    def get_available_periods(
        self,
        company: Company
    ) -> list[dict]:
        """
        Returns months with container activity for dropdown.

        Returns:
            [{'year': 2026, 'month': 1, 'label': 'Январь 2026', 'has_statement': True}, ...]
        """

    def delete_statement(
        self,
        statement: MonthlyStatement
    ) -> None:
        """Delete statement and all line items (for regeneration)."""
```

### StatementExportService

Location: `apps/billing/services/export_service.py`

```python
class StatementExportService:
    """Export statements to Excel and PDF formats."""

    def export_to_excel(self, statement: MonthlyStatement) -> BytesIO:
        """
        Generate Excel file from statement.

        Structure:
        - Header row with company info and period
        - Column headers
        - Data rows for each line item
        - Summary row at bottom
        """

    def export_to_pdf(self, statement: MonthlyStatement) -> BytesIO:
        """
        Generate PDF from statement using HTML template.

        Uses WeasyPrint to convert HTML to PDF.
        Template: templates/billing/statement_pdf.html
        """

    def _get_excel_filename(self, statement: MonthlyStatement) -> str:
        """Generate filename: statement_CompanyName_2026_01.xlsx"""

    def _get_pdf_filename(self, statement: MonthlyStatement) -> str:
        """Generate filename: statement_CompanyName_2026_01.pdf"""
```

---

## API Endpoints

### Customer Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/customer/billing/statements/` | List all statements |
| GET | `/api/customer/billing/statements/{year}/{month}/` | Get/generate specific statement |
| GET | `/api/customer/billing/statements/{year}/{month}/export/excel/` | Download Excel |
| GET | `/api/customer/billing/statements/{year}/{month}/export/pdf/` | Download PDF |
| GET | `/api/customer/billing/available-periods/` | Get months with activity |

### Response Format

```json
// GET /api/customer/billing/statements/2026/1/
{
    "success": true,
    "data": {
        "id": 42,
        "year": 2026,
        "month": 1,
        "month_name": "Январь",
        "billing_method": "split",
        "billing_method_display": "Раздельный расчёт",

        "summary": {
            "total_containers": 15,
            "total_billable_days": 87,
            "total_usd": "2450.00",
            "total_uzs": "31850000.00"
        },

        "line_items": [
            {
                "id": 1,
                "container_number": "MSCU1234567",
                "container_size": "40ft",
                "container_size_display": "40 фут",
                "container_status": "laden",
                "container_status_display": "Груженый",
                "period_start": "2026-01-01",
                "period_end": "2026-01-15",
                "is_still_on_terminal": false,
                "total_days": 15,
                "free_days": 3,
                "billable_days": 12,
                "daily_rate_usd": "15.00",
                "daily_rate_uzs": "195000.00",
                "amount_usd": "180.00",
                "amount_uzs": "2340000.00"
            }
        ],

        "generated_at": "2026-01-19T10:30:00Z"
    }
}
```

### Admin Endpoint (Optional)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/billing/statements/regenerate/` | Force regenerate statement |

---

## Frontend Implementation

### File Structure

```
frontend/src/
├── views/customer/
│   └── Billing.vue              # Main tabbed page (NEW - replaces StorageCosts.vue)
├── components/billing/
│   ├── CurrentCosts.vue         # Tab 1: Existing StorageCosts logic (EXTRACTED)
│   └── MonthlyStatements.vue    # Tab 2: Statement list/detail (NEW)
├── services/
│   └── billingService.ts        # API methods (EXTEND)
└── types/
    └── billing.ts               # TypeScript interfaces (EXTEND)
```

### Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│  💰 Биллинг                                                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ Текущие расходы  │  │ Ежемесячные счета │                │
│  └──────────────────┘  └──────────────────┘                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TAB 1: Current Costs                                        │
│  - Existing StorageCosts functionality                       │
│  - Real-time calculations                                    │
│  - Filters and export                                        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TAB 2: Monthly Statements                                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Год: [2026 ▼]   │  │ Месяц: [Янв ▼]  │  [🔄 Пересчитать]│
│  └─────────────────┘  └─────────────────┘                   │
│                                                              │
│  [Summary Cards: Containers | Days | USD | UZS]             │
│  [Billing Method Badge with tooltip]                        │
│  [Statement Table with line items]                          │
│  [Export Buttons: Excel | PDF]                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### TypeScript Interfaces

```typescript
// types/billing.ts

export interface MonthlyStatement {
  id: number
  year: number
  month: number
  month_name: string
  billing_method: 'split' | 'exit_month'
  billing_method_display: string
  summary: StatementSummary
  line_items: StatementLineItem[]
  generated_at: string
}

export interface StatementSummary {
  total_containers: number
  total_billable_days: number
  total_usd: string
  total_uzs: string
}

export interface StatementLineItem {
  id: number
  container_number: string
  container_size: '20ft' | '40ft'
  container_size_display: string
  container_status: 'laden' | 'empty'
  container_status_display: string
  period_start: string
  period_end: string
  is_still_on_terminal: boolean
  total_days: number
  free_days: number
  billable_days: number
  daily_rate_usd: string
  daily_rate_uzs: string
  amount_usd: string
  amount_uzs: string
}

export interface AvailablePeriod {
  year: number
  month: number
  label: string
  has_statement: boolean
}
```

---

## Dependencies

### Backend

Add to `requirements.txt`:
```
weasyprint>=60.0
```

Note: WeasyPrint requires system dependencies (cairo, pango). For Docker, add to Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

---

## Migration Plan

1. **Add models** — Create MonthlyStatement and StatementLineItem
2. **Add Company field** — Add billing_method to Company (with default 'split')
3. **Create services** — MonthlyStatementService and StatementExportService
4. **Create views** — Customer statement endpoints
5. **Create PDF template** — HTML template for PDF export
6. **Frontend refactor** — Transform StorageCosts to Billing with tabs
7. **Update navigation** — Change menu item from "Стоимость хранения" to "Биллинг"

---

## Testing Considerations

- Test split billing with container spanning multiple months
- Test exit-month billing captures full stay
- Test statement regeneration overwrites correctly
- Test PDF generation with various data lengths
- Test Excel export formatting
- Test customer can only see their own statements
- Test available-periods returns correct months

---

## Future Enhancements (Out of Scope)

- Email notifications when statements are generated
- Automated monthly statement generation (cron job)
- Payment status tracking
- Invoice numbering for legal compliance
- Multi-currency support beyond USD/UZS
