# Customer Billing & Monthly Statements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the customer "Storage Costs" page into a tabbed "Billing" page with monthly statements that customers can view, export to Excel/PDF, and reference historically.

**Architecture:** Hybrid on-demand generation with caching. Statements are calculated from live container data when first requested, then persisted for historical reference. Reuses existing `StorageCostService` for all cost calculations.

**Tech Stack:** Django 5.2, DRF, WeasyPrint (PDF), openpyxl (Excel), Vue 3, TypeScript, Ant Design Vue

---

## Task 1: Add billing_method to Company Model

**Files:**
- Modify: `backend/apps/accounts/models.py:334-401`
- Create: `backend/apps/accounts/migrations/0003_company_billing_method.py` (auto-generated)

**Step 1: Write the failing test**

Create: `backend/tests/accounts/test_company_billing_method.py`

```python
import pytest
from apps.accounts.models import Company


@pytest.mark.django_db
class TestCompanyBillingMethod:
    def test_company_has_billing_method_field(self):
        """Company should have billing_method field with default 'split'."""
        company = Company.objects.create(name="Test Company")
        assert hasattr(company, "billing_method")
        assert company.billing_method == "split"

    def test_company_billing_method_choices(self):
        """Company billing_method should accept 'split' and 'exit_month'."""
        company = Company.objects.create(name="Test Company", billing_method="exit_month")
        assert company.billing_method == "exit_month"

        company.billing_method = "split"
        company.save()
        company.refresh_from_db()
        assert company.billing_method == "split"
```

**Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/accounts/test_company_billing_method.py -v
```

Expected: FAIL with "Company has no attribute 'billing_method'"

**Step 3: Add BillingMethod choices and field to Company model**

Modify `backend/apps/accounts/models.py` - add after line 333 (before Company class):

```python
class BillingMethod(models.TextChoices):
    """Billing method for monthly statements."""

    SPLIT = "split", "Раздельный расчёт"
    EXIT_MONTH = "exit_month", "По месяцу выхода"
```

Add inside Company class (after `notifications_enabled` field, around line 374):

```python
    billing_method = models.CharField(
        max_length=20,
        choices=BillingMethod.choices,
        default=BillingMethod.SPLIT,
        verbose_name="Метод расчёта",
        help_text="Метод расчёта для ежемесячных выписок",
    )
```

**Step 4: Create and apply migration**

```bash
cd backend && python manage.py makemigrations accounts --name company_billing_method
cd backend && python manage.py migrate
```

**Step 5: Run test to verify it passes**

```bash
cd backend && pytest tests/accounts/test_company_billing_method.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add backend/apps/accounts/models.py backend/apps/accounts/migrations/ backend/tests/accounts/test_company_billing_method.py
git commit -m "feat(billing): add billing_method field to Company model

Adds configurable billing method per company:
- 'split': costs allocated to months they were incurred
- 'exit_month': full cost appears in container exit month

Default is 'split' for backward compatibility."
```

---

## Task 2: Create MonthlyStatement and StatementLineItem Models

**Files:**
- Modify: `backend/apps/billing/models.py`
- Create: `backend/apps/billing/migrations/0003_monthlystatement_statementlineitem.py` (auto-generated)

**Step 1: Write the failing test**

Create: `backend/tests/billing/test_statement_models.py`

```python
import pytest
from datetime import date
from decimal import Decimal

from apps.accounts.models import Company
from apps.billing.models import MonthlyStatement, StatementLineItem


@pytest.mark.django_db
class TestMonthlyStatementModel:
    def test_create_monthly_statement(self):
        """MonthlyStatement should be created with required fields."""
        company = Company.objects.create(name="Test Company")
        statement = MonthlyStatement.objects.create(
            company=company,
            year=2026,
            month=1,
            billing_method="split",
            total_containers=5,
            total_billable_days=45,
            total_usd=Decimal("500.00"),
            total_uzs=Decimal("6500000.00"),
        )
        assert statement.id is not None
        assert statement.company == company
        assert statement.year == 2026
        assert statement.month == 1
        assert statement.month_name == "Январь"

    def test_monthly_statement_unique_constraint(self):
        """Only one statement per company per month."""
        company = Company.objects.create(name="Test Company")
        MonthlyStatement.objects.create(
            company=company, year=2026, month=1, billing_method="split"
        )
        with pytest.raises(Exception):  # IntegrityError
            MonthlyStatement.objects.create(
                company=company, year=2026, month=1, billing_method="split"
            )


@pytest.mark.django_db
class TestStatementLineItemModel:
    def test_create_statement_line_item(self):
        """StatementLineItem should be created with required fields."""
        company = Company.objects.create(name="Test Company")
        statement = MonthlyStatement.objects.create(
            company=company, year=2026, month=1, billing_method="split"
        )
        line_item = StatementLineItem.objects.create(
            statement=statement,
            container_number="HDMU1234567",
            container_size="40ft",
            container_status="laden",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 15),
            total_days=15,
            free_days=3,
            billable_days=12,
            daily_rate_usd=Decimal("15.00"),
            daily_rate_uzs=Decimal("195000.00"),
            amount_usd=Decimal("180.00"),
            amount_uzs=Decimal("2340000.00"),
        )
        assert line_item.id is not None
        assert line_item.statement == statement
```

**Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/billing/test_statement_models.py -v
```

Expected: FAIL with "cannot import name 'MonthlyStatement'"

**Step 3: Add models to billing/models.py**

Add to `backend/apps/billing/models.py` after TariffRate class (after line 210):

```python
class MonthlyStatement(TimestampedModel):
    """
    Persisted monthly billing statement for a company.

    Statements are generated on-demand and cached for historical reference.
    Each statement contains line items for containers billed in that period.
    """

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="statements",
        verbose_name="Компания",
    )
    year = models.PositiveIntegerField(verbose_name="Год")
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Месяц",
    )
    billing_method = models.CharField(
        max_length=20,
        choices=[("split", "Раздельный расчёт"), ("exit_month", "По месяцу выхода")],
        verbose_name="Метод расчёта",
        help_text="Snapshot of billing method used at generation time",
    )

    # Cached totals
    total_containers = models.PositiveIntegerField(default=0, verbose_name="Всего контейнеров")
    total_billable_days = models.PositiveIntegerField(default=0, verbose_name="Оплачиваемых дней")
    total_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого USD"
    )
    total_uzs = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого UZS"
    )

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата формирования")
    generated_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_statements",
        verbose_name="Сформировано пользователем",
    )

    class Meta:
        verbose_name = "Ежемесячная выписка"
        verbose_name_plural = "Ежемесячные выписки"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "year", "month"],
                name="unique_statement_per_company_month",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "year", "month"], name="statement_company_period_idx"),
            models.Index(fields=["year", "month"], name="statement_period_idx"),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.month:02d}/{self.year}"

    @property
    def month_name(self) -> str:
        """Return Russian month name."""
        months = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
        ]
        return months[self.month - 1]

    @property
    def billing_method_display(self) -> str:
        """Return display name for billing method."""
        return "Раздельный расчёт" if self.billing_method == "split" else "По месяцу выхода"


class StatementLineItem(TimestampedModel):
    """
    Individual container cost entry within a statement.

    Stores a snapshot of container data at generation time so the statement
    remains accurate even if container data is later modified.
    """

    statement = models.ForeignKey(
        MonthlyStatement,
        on_delete=models.CASCADE,
        related_name="line_items",
        verbose_name="Выписка",
    )
    container_entry = models.ForeignKey(
        "terminal_operations.ContainerEntry",
        on_delete=models.SET_NULL,
        null=True,
        related_name="statement_line_items",
        verbose_name="Запись контейнера",
        help_text="Reference to original entry (may be null if deleted)",
    )

    # Snapshot data (won't change if container data updates)
    container_number = models.CharField(max_length=20, verbose_name="Номер контейнера")
    container_size = models.CharField(
        max_length=10,
        choices=ContainerSize.choices,
        verbose_name="Размер контейнера",
    )
    container_status = models.CharField(
        max_length=10,
        choices=ContainerBillingStatus.choices,
        verbose_name="Статус контейнера",
    )

    # Period for this statement (may be subset of total stay)
    period_start = models.DateField(verbose_name="Начало периода")
    period_end = models.DateField(verbose_name="Конец периода")
    is_still_on_terminal = models.BooleanField(default=False, verbose_name="На терминале")

    # Day breakdown
    total_days = models.PositiveIntegerField(verbose_name="Всего дней")
    free_days = models.PositiveIntegerField(verbose_name="Льготных дней")
    billable_days = models.PositiveIntegerField(verbose_name="Оплачиваемых дней")

    # Rates used
    daily_rate_usd = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Ставка USD/день"
    )
    daily_rate_uzs = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Ставка UZS/день"
    )

    # Calculated amounts
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Сумма USD")
    amount_uzs = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма UZS")

    class Meta:
        verbose_name = "Позиция выписки"
        verbose_name_plural = "Позиции выписки"
        ordering = ["container_number"]
        indexes = [
            models.Index(fields=["statement", "container_number"], name="lineitem_stmt_container_idx"),
        ]

    def __str__(self):
        return f"{self.container_number} ({self.statement})"

    @property
    def container_size_display(self) -> str:
        """Return display name for container size."""
        return "20 футов" if self.container_size == "20ft" else "40 футов"

    @property
    def container_status_display(self) -> str:
        """Return display name for container status."""
        return "Груженый" if self.container_status == "laden" else "Порожний"
```

Add import at top of file:

```python
from django.core.validators import MinValueValidator, MaxValueValidator
```

**Step 4: Create and apply migration**

```bash
cd backend && python manage.py makemigrations billing --name monthlystatement_statementlineitem
cd backend && python manage.py migrate
```

**Step 5: Run test to verify it passes**

```bash
cd backend && pytest tests/billing/test_statement_models.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add backend/apps/billing/models.py backend/apps/billing/migrations/ backend/tests/billing/test_statement_models.py
git commit -m "feat(billing): add MonthlyStatement and StatementLineItem models

Models for persisting monthly billing statements:
- MonthlyStatement: company, year, month, totals, metadata
- StatementLineItem: container snapshot with period-adjusted costs

Includes unique constraint per company/month and proper indexes."
```

---

## Task 3: Create MonthlyStatementService

**Files:**
- Create: `backend/apps/billing/services/statement_service.py`
- Create: `backend/tests/billing/test_statement_service.py`

**Step 1: Write the failing test**

Create: `backend/tests/billing/test_statement_service.py`

```python
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import Company, CustomUser
from apps.billing.models import MonthlyStatement, Tariff, TariffRate
from apps.billing.services.statement_service import MonthlyStatementService
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        username="admin", password="test123", user_type="admin"
    )


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", billing_method="split")


@pytest.fixture
def general_tariff(db, admin_user):
    tariff = Tariff.objects.create(
        effective_from=date(2025, 1, 1),
        created_by=admin_user,
    )
    TariffRate.objects.create(
        tariff=tariff,
        container_size="20ft",
        container_status="laden",
        daily_rate_usd=Decimal("10.00"),
        daily_rate_uzs=Decimal("130000.00"),
        free_days=3,
    )
    TariffRate.objects.create(
        tariff=tariff,
        container_size="40ft",
        container_status="laden",
        daily_rate_usd=Decimal("15.00"),
        daily_rate_uzs=Decimal("195000.00"),
        free_days=3,
    )
    return tariff


@pytest.fixture
def container(db):
    return Container.objects.create(
        container_number="HDMU1234567",
        iso_type="42G1",
    )


@pytest.fixture
def container_entry(db, container, company, admin_user):
    return ContainerEntry.objects.create(
        container=container,
        company=company,
        entry_time=timezone.make_aware(datetime(2026, 1, 5, 10, 0, 0)),
        status="LADEN",
        transport_type="TRUCK",
        transport_number="01A123BC",
        recorded_by=admin_user,
    )


@pytest.mark.django_db
class TestMonthlyStatementService:
    def test_get_or_generate_statement_creates_new(
        self, company, container_entry, general_tariff, admin_user
    ):
        """Service should create a new statement when none exists."""
        service = MonthlyStatementService()
        statement = service.get_or_generate_statement(
            company=company,
            year=2026,
            month=1,
            user=admin_user,
        )

        assert statement.id is not None
        assert statement.company == company
        assert statement.year == 2026
        assert statement.month == 1
        assert statement.total_containers >= 1
        assert statement.line_items.count() >= 1

    def test_get_or_generate_statement_returns_existing(
        self, company, container_entry, general_tariff, admin_user
    ):
        """Service should return existing statement without regenerating."""
        service = MonthlyStatementService()

        # First call creates
        statement1 = service.get_or_generate_statement(company, 2026, 1, user=admin_user)

        # Second call returns existing
        statement2 = service.get_or_generate_statement(company, 2026, 1, user=admin_user)

        assert statement1.id == statement2.id

    def test_get_or_generate_statement_regenerate(
        self, company, container_entry, general_tariff, admin_user
    ):
        """Service should regenerate when regenerate=True."""
        service = MonthlyStatementService()

        statement1 = service.get_or_generate_statement(company, 2026, 1, user=admin_user)
        original_generated_at = statement1.generated_at

        # Force regenerate
        statement2 = service.get_or_generate_statement(
            company, 2026, 1, user=admin_user, regenerate=True
        )

        assert statement2.id == statement1.id  # Same record, updated
        assert statement2.generated_at > original_generated_at

    def test_get_available_periods(self, company, container_entry, general_tariff):
        """Service should return months with container activity."""
        service = MonthlyStatementService()
        periods = service.get_available_periods(company)

        assert len(periods) >= 1
        assert any(p["year"] == 2026 and p["month"] == 1 for p in periods)
```

**Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/billing/test_statement_service.py -v
```

Expected: FAIL with "No module named 'apps.billing.services.statement_service'"

**Step 3: Create the service**

Create: `backend/apps/billing/services/statement_service.py`

```python
"""
Monthly statement generation service.

This service handles the generation and management of monthly billing statements.
It reuses StorageCostService for all cost calculations to avoid duplication.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.core.services.base_service import BaseService

from ..models import MonthlyStatement, StatementLineItem
from .storage_cost_service import StorageCostService


if TYPE_CHECKING:
    from apps.accounts.models import Company, CustomUser
    from apps.terminal_operations.models import ContainerEntry


@dataclass
class AvailablePeriod:
    """A month that has container activity for a company."""

    year: int
    month: int
    label: str
    has_statement: bool


class MonthlyStatementService(BaseService):
    """
    Service for generating and managing monthly billing statements.

    The service uses a hybrid approach:
    - Statements are calculated on-demand from live container data
    - Once generated, they are persisted for historical reference
    - Regeneration is supported for corrections

    Billing methods:
    - 'split': Costs allocated to months they were incurred
    - 'exit_month': Full cost appears in container exit month
    """

    MONTH_NAMES = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]

    def __init__(self):
        super().__init__()
        self.storage_cost_service = StorageCostService()

    def get_or_generate_statement(
        self,
        company: "Company",
        year: int,
        month: int,
        user: "CustomUser | None" = None,
        regenerate: bool = False,
    ) -> MonthlyStatement:
        """
        Get existing statement or generate new one.

        Args:
            company: The company to generate statement for
            year: Statement year
            month: Statement month (1-12)
            user: User requesting generation (for audit)
            regenerate: If True, recalculates even if exists

        Returns:
            MonthlyStatement with populated line_items
        """
        # Check for existing statement
        existing = MonthlyStatement.objects.filter(
            company=company, year=year, month=month
        ).first()

        if existing and not regenerate:
            self.logger.info(f"Returning existing statement {existing.id}")
            return existing

        # Generate (or regenerate) the statement
        return self._generate_statement(company, year, month, user, existing)

    @transaction.atomic
    def _generate_statement(
        self,
        company: "Company",
        year: int,
        month: int,
        user: "CustomUser | None",
        existing: MonthlyStatement | None,
    ) -> MonthlyStatement:
        """
        Core statement generation logic.

        1. Determine billing method from company
        2. Calculate month boundaries
        3. Find relevant containers based on billing method
        4. Calculate costs using StorageCostService
        5. Create/update statement and line items
        """
        from apps.accounts.models import BillingMethod

        billing_method = company.billing_method
        month_start, month_end = self._get_month_boundaries(year, month)

        self.logger.info(
            f"Generating statement for {company.name} - {year}/{month} "
            f"(method={billing_method})"
        )

        # Get relevant container entries based on billing method
        if billing_method == BillingMethod.SPLIT:
            entries = self._get_containers_for_split_billing(company, month_start, month_end)
        else:
            entries = self._get_containers_for_exit_billing(company, month_start, month_end)

        # Delete existing line items if regenerating
        if existing:
            existing.line_items.all().delete()
            statement = existing
            statement.billing_method = billing_method
            statement.generated_at = timezone.now()
            statement.generated_by = user
        else:
            statement = MonthlyStatement(
                company=company,
                year=year,
                month=month,
                billing_method=billing_method,
                generated_by=user,
            )
            statement.save()

        # Generate line items
        total_usd = Decimal("0.00")
        total_uzs = Decimal("0.00")
        total_billable_days = 0
        line_items_created = 0

        for entry in entries:
            try:
                line_item = self._create_line_item(
                    statement=statement,
                    entry=entry,
                    month_start=month_start,
                    month_end=month_end,
                    billing_method=billing_method,
                )
                if line_item:
                    total_usd += line_item.amount_usd
                    total_uzs += line_item.amount_uzs
                    total_billable_days += line_item.billable_days
                    line_items_created += 1
            except Exception as e:
                self.logger.warning(f"Failed to create line item for entry {entry.id}: {e}")
                continue

        # Update statement totals
        statement.total_containers = line_items_created
        statement.total_billable_days = total_billable_days
        statement.total_usd = total_usd
        statement.total_uzs = total_uzs
        statement.save()

        self.logger.info(
            f"Generated statement {statement.id}: {line_items_created} containers, "
            f"${total_usd} USD, {total_uzs} UZS"
        )

        return statement

    def _create_line_item(
        self,
        statement: MonthlyStatement,
        entry: "ContainerEntry",
        month_start: date,
        month_end: date,
        billing_method: str,
    ) -> StatementLineItem | None:
        """Create a line item for a container entry."""
        from apps.accounts.models import BillingMethod

        # Calculate cost for the entry
        cost_result = self.storage_cost_service.calculate_cost(entry)

        if billing_method == BillingMethod.SPLIT:
            # For split billing, only include days within the month
            period_start = max(cost_result.entry_date, month_start)
            period_end = min(cost_result.end_date, month_end)

            if period_start > period_end:
                return None  # No overlap with this month

            # Calculate days and amounts for this period only
            total_days = (period_end - period_start).days + 1

            # Proportionally calculate amounts based on period overlap
            full_days = cost_result.total_days
            if full_days > 0:
                ratio = Decimal(total_days) / Decimal(full_days)
                amount_usd = (cost_result.total_usd * ratio).quantize(Decimal("0.01"))
                amount_uzs = (cost_result.total_uzs * ratio).quantize(Decimal("0.01"))

                # Calculate proportional free/billable days
                free_days = min(cost_result.free_days_applied, total_days)
                billable_days = total_days - free_days
            else:
                amount_usd = Decimal("0.00")
                amount_uzs = Decimal("0.00")
                free_days = 0
                billable_days = 0
        else:
            # For exit-month billing, include full cost
            period_start = cost_result.entry_date
            period_end = cost_result.end_date
            total_days = cost_result.total_days
            free_days = cost_result.free_days_applied
            billable_days = cost_result.billable_days
            amount_usd = cost_result.total_usd
            amount_uzs = cost_result.total_uzs

        # Get daily rate from first period (for display)
        daily_rate_usd = Decimal("0.00")
        daily_rate_uzs = Decimal("0.00")
        if cost_result.periods:
            daily_rate_usd = cost_result.periods[0].daily_rate_usd
            daily_rate_uzs = cost_result.periods[0].daily_rate_uzs

        return StatementLineItem.objects.create(
            statement=statement,
            container_entry=entry,
            container_number=cost_result.container_number,
            container_size=cost_result.container_size,
            container_status=cost_result.container_status,
            period_start=period_start,
            period_end=period_end,
            is_still_on_terminal=cost_result.is_active,
            total_days=total_days,
            free_days=free_days,
            billable_days=billable_days,
            daily_rate_usd=daily_rate_usd,
            daily_rate_uzs=daily_rate_uzs,
            amount_usd=amount_usd,
            amount_uzs=amount_uzs,
        )

    def _get_containers_for_split_billing(
        self,
        company: "Company",
        month_start: date,
        month_end: date,
    ) -> QuerySet["ContainerEntry"]:
        """
        Find containers active during any part of the month.

        Containers are included if:
        - Entry before month end AND
        - (Exit after month start OR still on terminal)
        """
        from apps.terminal_operations.models import ContainerEntry

        return ContainerEntry.objects.filter(
            company=company,
            entry_time__date__lte=month_end,
        ).filter(
            Q(exit_date__isnull=True) | Q(exit_date__date__gte=month_start)
        ).select_related("container", "company")

    def _get_containers_for_exit_billing(
        self,
        company: "Company",
        month_start: date,
        month_end: date,
    ) -> QuerySet["ContainerEntry"]:
        """Find containers that exited during the month."""
        from apps.terminal_operations.models import ContainerEntry

        return ContainerEntry.objects.filter(
            company=company,
            exit_date__date__gte=month_start,
            exit_date__date__lte=month_end,
        ).select_related("container", "company")

    def _get_month_boundaries(self, year: int, month: int) -> tuple[date, date]:
        """Get first and last day of a month."""
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        return first_day, last_day

    def list_statements(
        self,
        company: "Company",
        year: int | None = None,
    ) -> QuerySet[MonthlyStatement]:
        """List all statements for a company, optionally filtered by year."""
        queryset = MonthlyStatement.objects.filter(company=company)
        if year:
            queryset = queryset.filter(year=year)
        return queryset.prefetch_related("line_items")

    def get_available_periods(
        self,
        company: "Company",
    ) -> list[dict]:
        """
        Returns months with container activity for dropdown.

        Scans container entries to find months with activity,
        marks which months already have generated statements.
        """
        from apps.terminal_operations.models import ContainerEntry

        # Get all months with container activity
        entries = ContainerEntry.objects.filter(company=company).values_list(
            "entry_time", flat=True
        )

        # Get existing statements
        existing_statements = set(
            MonthlyStatement.objects.filter(company=company).values_list(
                "year", "month"
            )
        )

        # Collect unique months
        periods_set = set()
        for entry_time in entries:
            if entry_time:
                periods_set.add((entry_time.year, entry_time.month))

        # Sort and format
        periods = []
        for year, month in sorted(periods_set, reverse=True):
            periods.append({
                "year": year,
                "month": month,
                "label": f"{self.MONTH_NAMES[month - 1]} {year}",
                "has_statement": (year, month) in existing_statements,
            })

        return periods

    def delete_statement(self, statement: MonthlyStatement) -> None:
        """Delete statement and all line items."""
        statement_id = statement.id
        statement.delete()
        self.logger.info(f"Deleted statement {statement_id}")
```

**Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/billing/test_statement_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/apps/billing/services/statement_service.py backend/tests/billing/test_statement_service.py
git commit -m "feat(billing): add MonthlyStatementService for statement generation

Service for generating and managing monthly billing statements:
- Hybrid on-demand + cached generation
- Split billing (costs per month) and exit-month billing
- Reuses StorageCostService for calculations
- get_available_periods for UI dropdowns"
```

---

## Task 4: Create Statement API Endpoints

**Files:**
- Modify: `backend/apps/billing/views.py`
- Modify: `backend/apps/billing/urls.py`
- Create: `backend/apps/billing/serializers.py` (or modify existing)

**Step 1: Write the failing test**

Create: `backend/tests/billing/test_statement_api.py`

```python
import pytest
from datetime import date, datetime
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Company, CustomUser, CustomerProfile
from apps.billing.models import Tariff, TariffRate
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer_user(db):
    user = CustomUser.objects.create_user(
        username="customer", password="test123", user_type="customer"
    )
    return user


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", billing_method="split")


@pytest.fixture
def customer_with_profile(customer_user, company):
    CustomerProfile.objects.create(
        user=customer_user,
        company=company,
        phone_number="+998901234567",
    )
    return customer_user


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        username="admin", password="test123", user_type="admin"
    )


@pytest.fixture
def general_tariff(db, admin_user):
    tariff = Tariff.objects.create(
        effective_from=date(2025, 1, 1),
        created_by=admin_user,
    )
    TariffRate.objects.create(
        tariff=tariff,
        container_size="40ft",
        container_status="laden",
        daily_rate_usd=Decimal("15.00"),
        daily_rate_uzs=Decimal("195000.00"),
        free_days=3,
    )
    return tariff


@pytest.fixture
def container(db):
    return Container.objects.create(container_number="HDMU1234567", iso_type="42G1")


@pytest.fixture
def container_entry(db, container, company, admin_user):
    return ContainerEntry.objects.create(
        container=container,
        company=company,
        entry_time=timezone.make_aware(datetime(2026, 1, 5, 10, 0, 0)),
        status="LADEN",
        transport_type="TRUCK",
        transport_number="01A123BC",
        recorded_by=admin_user,
    )


@pytest.mark.django_db
class TestStatementAPI:
    def test_get_statement_unauthenticated(self, api_client):
        """Unauthenticated requests should be rejected."""
        url = "/api/customer/billing/statements/2026/1/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_statement_authenticated(
        self, api_client, customer_with_profile, company, container_entry, general_tariff
    ):
        """Authenticated customer should get/generate statement."""
        api_client.force_authenticate(user=customer_with_profile)
        url = "/api/customer/billing/statements/2026/1/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["year"] == 2026
        assert response.data["data"]["month"] == 1
        assert "line_items" in response.data["data"]

    def test_get_available_periods(
        self, api_client, customer_with_profile, company, container_entry, general_tariff
    ):
        """Customer should get available billing periods."""
        api_client.force_authenticate(user=customer_with_profile)
        url = "/api/customer/billing/available-periods/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["data"]) >= 1
```

**Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/billing/test_statement_api.py -v
```

Expected: FAIL with 404 (URL not found)

**Step 3: Create serializers**

Add to `backend/apps/billing/serializers.py` (create if doesn't exist):

```python
from decimal import Decimal

from rest_framework import serializers

from .models import MonthlyStatement, StatementLineItem


class StatementLineItemSerializer(serializers.ModelSerializer):
    """Serializer for statement line items."""

    container_size_display = serializers.CharField(read_only=True)
    container_status_display = serializers.CharField(read_only=True)

    class Meta:
        model = StatementLineItem
        fields = [
            "id",
            "container_number",
            "container_size",
            "container_size_display",
            "container_status",
            "container_status_display",
            "period_start",
            "period_end",
            "is_still_on_terminal",
            "total_days",
            "free_days",
            "billable_days",
            "daily_rate_usd",
            "daily_rate_uzs",
            "amount_usd",
            "amount_uzs",
        ]


class MonthlyStatementSerializer(serializers.ModelSerializer):
    """Serializer for monthly statements."""

    month_name = serializers.CharField(read_only=True)
    billing_method_display = serializers.CharField(read_only=True)
    line_items = StatementLineItemSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyStatement
        fields = [
            "id",
            "year",
            "month",
            "month_name",
            "billing_method",
            "billing_method_display",
            "summary",
            "line_items",
            "generated_at",
        ]

    def get_summary(self, obj: MonthlyStatement) -> dict:
        return {
            "total_containers": obj.total_containers,
            "total_billable_days": obj.total_billable_days,
            "total_usd": str(obj.total_usd),
            "total_uzs": str(obj.total_uzs),
        }


class AvailablePeriodSerializer(serializers.Serializer):
    """Serializer for available billing periods."""

    year = serializers.IntegerField()
    month = serializers.IntegerField()
    label = serializers.CharField()
    has_statement = serializers.BooleanField()
```

**Step 4: Create views**

Add to `backend/apps/billing/views.py` (at the end of file):

```python
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customer_portal.permissions import IsCustomer

from .serializers import (
    AvailablePeriodSerializer,
    MonthlyStatementSerializer,
)
from .services.statement_service import MonthlyStatementService


class CustomerStatementView(APIView):
    """
    Get or generate a monthly statement for the authenticated customer's company.

    GET /api/customer/billing/statements/{year}/{month}/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        # Get customer's company
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = profile.company

        # Validate month
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for regenerate flag
        regenerate = request.query_params.get("regenerate", "").lower() == "true"

        # Get or generate statement
        service = MonthlyStatementService()
        statement = service.get_or_generate_statement(
            company=company,
            year=year,
            month=month,
            user=request.user,
            regenerate=regenerate,
        )

        serializer = MonthlyStatementSerializer(statement)
        return Response({"success": True, "data": serializer.data})


class CustomerStatementListView(APIView):
    """
    List all statements for the authenticated customer's company.

    GET /api/customer/billing/statements/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        year = request.query_params.get("year")
        service = MonthlyStatementService()
        statements = service.list_statements(
            company=profile.company,
            year=int(year) if year else None,
        )

        serializer = MonthlyStatementSerializer(statements, many=True)
        return Response({"success": True, "data": serializer.data})


class CustomerAvailablePeriodsView(APIView):
    """
    Get available billing periods for dropdown.

    GET /api/customer/billing/available-periods/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = MonthlyStatementService()
        periods = service.get_available_periods(profile.company)

        serializer = AvailablePeriodSerializer(periods, many=True)
        return Response({"success": True, "data": serializer.data})
```

**Step 5: Add URLs**

Add to `backend/apps/billing/urls.py`:

```python
from django.urls import path

from .views import (
    CustomerAvailablePeriodsView,
    CustomerStatementListView,
    CustomerStatementView,
    # ... existing views ...
)

# Add to urlpatterns:
urlpatterns = [
    # ... existing patterns ...

    # Customer billing endpoints
    path(
        "customer/billing/statements/",
        CustomerStatementListView.as_view(),
        name="customer-statement-list",
    ),
    path(
        "customer/billing/statements/<int:year>/<int:month>/",
        CustomerStatementView.as_view(),
        name="customer-statement-detail",
    ),
    path(
        "customer/billing/available-periods/",
        CustomerAvailablePeriodsView.as_view(),
        name="customer-available-periods",
    ),
]
```

Ensure URLs are included in main urls.py if not already:

```python
# In terminal_app/urls.py, should have:
path("api/", include("apps.billing.urls")),
```

**Step 6: Run test to verify it passes**

```bash
cd backend && pytest tests/billing/test_statement_api.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add backend/apps/billing/serializers.py backend/apps/billing/views.py backend/apps/billing/urls.py backend/tests/billing/test_statement_api.py
git commit -m "feat(billing): add customer statement API endpoints

Customer-facing endpoints:
- GET /api/customer/billing/statements/ - list all statements
- GET /api/customer/billing/statements/{year}/{month}/ - get/generate statement
- GET /api/customer/billing/available-periods/ - periods dropdown data

Includes regenerate query param for forcing recalculation."
```

---

## Task 5: Add Export Endpoints (Excel + PDF)

**Files:**
- Create: `backend/apps/billing/services/export_service.py`
- Modify: `backend/apps/billing/views.py`
- Modify: `backend/apps/billing/urls.py`
- Create: `backend/templates/billing/statement_pdf.html`
- Modify: `backend/requirements.txt`

**Step 1: Install WeasyPrint**

```bash
cd backend && pip install weasyprint && pip freeze | grep -i weasy >> requirements.txt
```

**Step 2: Create export service**

Create: `backend/apps/billing/services/export_service.py`

```python
"""
Statement export service for Excel and PDF generation.
"""

from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from apps.core.services.base_service import BaseService


if TYPE_CHECKING:
    from ..models import MonthlyStatement


class StatementExportService(BaseService):
    """Service for exporting statements to Excel and PDF formats."""

    def export_to_excel(self, statement: "MonthlyStatement") -> BytesIO:
        """Generate Excel file from statement."""
        wb = Workbook()
        ws = wb.active
        ws.title = f"Выписка {statement.month:02d}-{statement.year}"

        # Styles
        header_font = Font(bold=True, size=14)
        subheader_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_text = Font(bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Title section
        ws.merge_cells("A1:H1")
        ws["A1"] = f"Выписка за {statement.month_name} {statement.year}"
        ws["A1"].font = header_font
        ws["A1"].alignment = Alignment(horizontal="center")

        ws["A3"] = f"Компания: {statement.company.name}"
        ws["A4"] = f"Метод расчёта: {statement.billing_method_display}"
        ws["A5"] = f"Дата формирования: {statement.generated_at.strftime('%d.%m.%Y %H:%M')}"

        # Summary section
        ws["A7"] = "ИТОГО:"
        ws["A7"].font = subheader_font
        ws["A8"] = f"Контейнеров: {statement.total_containers}"
        ws["A9"] = f"Оплачиваемых дней: {statement.total_billable_days}"
        ws["A10"] = f"Сумма USD: ${statement.total_usd:,.2f}"
        ws["A11"] = f"Сумма UZS: {statement.total_uzs:,.0f} сум"

        # Table headers
        headers = [
            "Контейнер",
            "Размер",
            "Статус",
            "Начало",
            "Конец",
            "Всего дней",
            "Льготных",
            "Оплачиваемых",
            "Ставка USD",
            "Сумма USD",
            "Сумма UZS",
        ]

        row = 13
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_text
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center")

        # Table data
        for item in statement.line_items.all():
            row += 1
            data = [
                item.container_number,
                item.container_size_display,
                item.container_status_display,
                item.period_start.strftime("%d.%m.%Y"),
                item.period_end.strftime("%d.%m.%Y") if not item.is_still_on_terminal else "На терминале",
                item.total_days,
                item.free_days,
                item.billable_days,
                float(item.daily_rate_usd),
                float(item.amount_usd),
                float(item.amount_uzs),
            ]
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = thin_border
                if col >= 6:  # Numbers
                    cell.alignment = Alignment(horizontal="right")

        # Adjust column widths
        column_widths = [15, 10, 12, 12, 14, 10, 10, 12, 12, 12, 15]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    def export_to_pdf(self, statement: "MonthlyStatement") -> BytesIO:
        """Generate PDF from statement using HTML template."""
        from weasyprint import HTML

        # Render HTML template
        html_content = render_to_string(
            "billing/statement_pdf.html",
            {
                "statement": statement,
                "line_items": statement.line_items.all(),
            },
        )

        # Convert to PDF
        output = BytesIO()
        HTML(string=html_content).write_pdf(output)
        output.seek(0)
        return output

    def get_excel_filename(self, statement: "MonthlyStatement") -> str:
        """Generate filename for Excel export."""
        company_slug = statement.company.slug or "company"
        return f"statement_{company_slug}_{statement.year}_{statement.month:02d}.xlsx"

    def get_pdf_filename(self, statement: "MonthlyStatement") -> str:
        """Generate filename for PDF export."""
        company_slug = statement.company.slug or "company"
        return f"statement_{company_slug}_{statement.year}_{statement.month:02d}.pdf"
```

**Step 3: Create PDF template**

Create directory: `backend/templates/billing/`

Create: `backend/templates/billing/statement_pdf.html`

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Выписка {{ statement.month_name }} {{ statement.year }}</title>
    <style>
        body {
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
            margin: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #4472C4;
            padding-bottom: 15px;
        }
        .header h1 {
            color: #4472C4;
            margin: 0 0 10px 0;
            font-size: 24px;
        }
        .company-info {
            margin-bottom: 20px;
        }
        .company-info p {
            margin: 5px 0;
        }
        .summary {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary h3 {
            margin: 0 0 10px 0;
            color: #4472C4;
        }
        .summary-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        .summary-item {
            flex: 1;
            min-width: 150px;
        }
        .summary-item .label {
            font-size: 11px;
            color: #666;
        }
        .summary-item .value {
            font-size: 16px;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background: #4472C4;
            color: white;
            padding: 10px 5px;
            text-align: left;
            font-size: 11px;
        }
        td {
            padding: 8px 5px;
            border-bottom: 1px solid #ddd;
            font-size: 11px;
        }
        tr:nth-child(even) {
            background: #f9f9f9;
        }
        .number {
            text-align: right;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            font-size: 10px;
            color: #666;
            border-top: 1px solid #ddd;
            padding-top: 15px;
        }
        .on-terminal {
            color: #52c41a;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>MTT Container Terminal</h1>
        <p>ВЫПИСКА ЗА {{ statement.month_name|upper }} {{ statement.year }}</p>
    </div>

    <div class="company-info">
        <p><strong>Компания:</strong> {{ statement.company.name }}</p>
        <p><strong>Метод расчёта:</strong> {{ statement.billing_method_display }}</p>
        <p><strong>Дата формирования:</strong> {{ statement.generated_at|date:"d.m.Y H:i" }}</p>
    </div>

    <div class="summary">
        <h3>ИТОГО</h3>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="label">Контейнеров</div>
                <div class="value">{{ statement.total_containers }}</div>
            </div>
            <div class="summary-item">
                <div class="label">Оплачиваемых дней</div>
                <div class="value">{{ statement.total_billable_days }}</div>
            </div>
            <div class="summary-item">
                <div class="label">Сумма (USD)</div>
                <div class="value">${{ statement.total_usd|floatformat:2 }}</div>
            </div>
            <div class="summary-item">
                <div class="label">Сумма (UZS)</div>
                <div class="value">{{ statement.total_uzs|floatformat:0 }} сум</div>
            </div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Контейнер</th>
                <th>Размер</th>
                <th>Статус</th>
                <th>Начало</th>
                <th>Конец</th>
                <th class="number">Дней</th>
                <th class="number">Льгот.</th>
                <th class="number">Опл.</th>
                <th class="number">USD</th>
                <th class="number">UZS</th>
            </tr>
        </thead>
        <tbody>
            {% for item in line_items %}
            <tr>
                <td>{{ item.container_number }}</td>
                <td>{{ item.container_size_display }}</td>
                <td>{{ item.container_status_display }}</td>
                <td>{{ item.period_start|date:"d.m.Y" }}</td>
                <td>
                    {% if item.is_still_on_terminal %}
                    <span class="on-terminal">На терминале</span>
                    {% else %}
                    {{ item.period_end|date:"d.m.Y" }}
                    {% endif %}
                </td>
                <td class="number">{{ item.total_days }}</td>
                <td class="number">{{ item.free_days }}</td>
                <td class="number">{{ item.billable_days }}</td>
                <td class="number">${{ item.amount_usd|floatformat:2 }}</td>
                <td class="number">{{ item.amount_uzs|floatformat:0 }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="footer">
        Сформировано автоматически системой MTT Container Terminal
    </div>
</body>
</html>
```

**Step 4: Add export views**

Add to `backend/apps/billing/views.py`:

```python
from django.http import HttpResponse

from .services.export_service import StatementExportService


class CustomerStatementExportExcelView(APIView):
    """Export statement to Excel."""

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or generate statement
        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company,
            year=year,
            month=month,
            user=request.user,
        )

        # Export to Excel
        export_service = StatementExportService()
        excel_file = export_service.export_to_excel(statement)
        filename = export_service.get_excel_filename(statement)

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class CustomerStatementExportPdfView(APIView):
    """Export statement to PDF."""

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or generate statement
        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company,
            year=year,
            month=month,
            user=request.user,
        )

        # Export to PDF
        export_service = StatementExportService()
        pdf_file = export_service.export_to_pdf(statement)
        filename = export_service.get_pdf_filename(statement)

        response = HttpResponse(pdf_file.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
```

**Step 5: Add export URLs**

Add to `backend/apps/billing/urls.py`:

```python
from .views import (
    CustomerStatementExportExcelView,
    CustomerStatementExportPdfView,
    # ... existing views ...
)

# Add to urlpatterns:
path(
    "customer/billing/statements/<int:year>/<int:month>/export/excel/",
    CustomerStatementExportExcelView.as_view(),
    name="customer-statement-export-excel",
),
path(
    "customer/billing/statements/<int:year>/<int:month>/export/pdf/",
    CustomerStatementExportPdfView.as_view(),
    name="customer-statement-export-pdf",
),
```

**Step 6: Run tests**

```bash
cd backend && pytest tests/billing/ -v
```

**Step 7: Commit**

```bash
git add backend/apps/billing/services/export_service.py backend/apps/billing/views.py backend/apps/billing/urls.py backend/templates/billing/ backend/requirements.txt
git commit -m "feat(billing): add Excel and PDF export for statements

Export service with:
- Excel export with styled headers and summary
- PDF export using WeasyPrint and HTML template
- Proper filename generation

Endpoints:
- GET /api/customer/billing/statements/{year}/{month}/export/excel/
- GET /api/customer/billing/statements/{year}/{month}/export/pdf/"
```

---

## Task 6: Create Frontend Billing Page with Tabs

**Files:**
- Create: `frontend/src/views/customer/Billing.vue`
- Create: `frontend/src/components/billing/CurrentCosts.vue`
- Create: `frontend/src/components/billing/MonthlyStatements.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/CustomerLayout.vue`
- Delete: `frontend/src/views/customer/StorageCosts.vue` (replaced by Billing.vue)

**Step 1: Create Billing page with tabs**

Create: `frontend/src/views/customer/Billing.vue`

```vue
<template>
  <a-card :bordered="false" class="billing-card">
    <template #title>
      <div class="card-title">
        <DollarOutlined style="color: #52c41a; margin-right: 8px;" />
        Биллинг
      </div>
    </template>

    <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
      <a-tab-pane key="current" tab="Текущие расходы">
        <CurrentCosts />
      </a-tab-pane>
      <a-tab-pane key="statements" tab="Ежемесячные счета">
        <MonthlyStatements />
      </a-tab-pane>
    </a-tabs>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { DollarOutlined } from '@ant-design/icons-vue';
import CurrentCosts from '../../components/billing/CurrentCosts.vue';
import MonthlyStatements from '../../components/billing/MonthlyStatements.vue';

const route = useRoute();
const router = useRouter();

const activeTab = ref<string>('current');

onMounted(() => {
  // Check for tab query param
  const tab = route.query.tab as string;
  if (tab === 'statements') {
    activeTab.value = 'statements';
  }
});

const handleTabChange = (key: string) => {
  router.replace({ query: { ...route.query, tab: key === 'current' ? undefined : key } });
};
</script>

<style scoped>
.billing-card {
  border-radius: 2px;
}

.card-title {
  display: flex;
  align-items: center;
}
</style>
```

**Step 2: Extract CurrentCosts component**

Create: `frontend/src/components/billing/CurrentCosts.vue`

Copy the entire content from `StorageCosts.vue` into this file, removing the outer card wrapper (keep just the inner content). The component structure stays the same but is now a child of Billing.vue.

**Step 3: Create MonthlyStatements component**

Create: `frontend/src/components/billing/MonthlyStatements.vue`

```vue
<template>
  <div class="monthly-statements">
    <!-- Period Selectors -->
    <a-space wrap style="margin-bottom: 16px;">
      <a-select
        v-model:value="selectedYear"
        placeholder="Год"
        style="width: 120px"
        :loading="periodsLoading"
        @change="handlePeriodChange"
      >
        <a-select-option v-for="year in availableYears" :key="year" :value="year">
          {{ year }}
        </a-select-option>
      </a-select>

      <a-select
        v-model:value="selectedMonth"
        placeholder="Месяц"
        style="width: 160px"
        :loading="periodsLoading"
        @change="handlePeriodChange"
      >
        <a-select-option
          v-for="period in filteredMonths"
          :key="`${period.year}-${period.month}`"
          :value="period.month"
        >
          {{ period.label }}
          <a-tag v-if="period.has_statement" color="green" size="small" style="margin-left: 8px;">
            Сформирован
          </a-tag>
        </a-select-option>
      </a-select>

      <a-button
        type="primary"
        :loading="loading"
        :disabled="!selectedYear || !selectedMonth"
        @click="fetchStatement"
      >
        <template #icon><SearchOutlined /></template>
        Показать
      </a-button>

      <a-button
        v-if="statement"
        :loading="regenerating"
        @click="regenerateStatement"
      >
        <template #icon><ReloadOutlined /></template>
        Пересчитать
      </a-button>
    </a-space>

    <!-- Statement Content -->
    <template v-if="statement">
      <!-- Billing Method Badge -->
      <a-alert
        :message="`Метод расчёта: ${statement.billing_method_display}`"
        type="info"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #icon><InfoCircleOutlined /></template>
      </a-alert>

      <!-- Summary Statistics -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 20px;">
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Всего контейнеров"
            :value="statement.summary.total_containers"
            :value-style="{ color: '#1677ff' }"
          >
            <template #prefix><ContainerOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Оплачиваемых дней"
            :value="statement.summary.total_billable_days"
            :value-style="{ color: '#fa8c16' }"
          >
            <template #prefix><CalendarOutlined /></template>
          </a-statistic>
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Итого (USD)"
            :value="formatCurrency(statement.summary.total_usd, 'USD')"
            :value-style="{ color: '#52c41a' }"
          />
        </a-col>
        <a-col :xs="12" :sm="6">
          <a-statistic
            title="Итого (UZS)"
            :value="formatCurrency(statement.summary.total_uzs, 'UZS')"
            :value-style="{ color: '#722ed1' }"
          />
        </a-col>
      </a-row>

      <a-divider style="margin: 12px 0;" />

      <!-- Export Buttons -->
      <a-space style="margin-bottom: 16px;">
        <a-button type="primary" @click="exportExcel">
          <template #icon><FileExcelOutlined /></template>
          Excel
        </a-button>
        <a-button @click="exportPdf">
          <template #icon><FilePdfOutlined /></template>
          PDF
        </a-button>
      </a-space>

      <!-- Line Items Table -->
      <a-table
        :columns="columns"
        :data-source="statement.line_items"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 1200 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'container'">
            <a-tag color="blue">{{ record.container_number }}</a-tag>
            <div style="font-size: 11px; color: #999; margin-top: 2px;">
              {{ record.container_size_display }} / {{ record.container_status_display }}
            </div>
          </template>
          <template v-if="column.key === 'period'">
            <div>{{ formatDate(record.period_start) }}</div>
            <div class="period-end">
              <template v-if="record.is_still_on_terminal">
                <a-tag color="green" size="small">На терминале</a-tag>
              </template>
              <template v-else>
                {{ formatDate(record.period_end) }}
              </template>
            </div>
          </template>
          <template v-if="column.key === 'days'">
            <div class="days-breakdown">
              <a-tag color="blue">{{ record.total_days }} всего</a-tag>
              <a-tag color="green">{{ record.free_days }} льгот.</a-tag>
              <a-tag color="orange">{{ record.billable_days }} опл.</a-tag>
            </div>
          </template>
          <template v-if="column.key === 'rate'">
            <span>${{ parseFloat(record.daily_rate_usd).toFixed(2) }}/день</span>
          </template>
          <template v-if="column.key === 'amount_usd'">
            <span class="amount-usd">${{ parseFloat(record.amount_usd).toFixed(2) }}</span>
          </template>
          <template v-if="column.key === 'amount_uzs'">
            <span class="amount-uzs">{{ formatUzs(record.amount_uzs) }}</span>
          </template>
        </template>
      </a-table>

      <!-- Generation Info -->
      <div style="margin-top: 16px; color: #999; font-size: 12px;">
        Сформировано: {{ formatDateTime(statement.generated_at) }}
      </div>
    </template>

    <!-- Empty State -->
    <a-empty
      v-else-if="!loading && selectedYear && selectedMonth"
      description="Выберите период и нажмите 'Показать'"
    />
    <a-empty
      v-else-if="!loading"
      description="Выберите год и месяц для просмотра выписки"
    />

    <!-- Loading -->
    <a-spin v-if="loading" style="display: block; text-align: center; padding: 40px;" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import type { TableProps } from 'ant-design-vue';
import {
  SearchOutlined,
  ReloadOutlined,
  ContainerOutlined,
  CalendarOutlined,
  InfoCircleOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
} from '@ant-design/icons-vue';
import { http } from '../../utils/httpClient';

interface StatementLineItem {
  id: number;
  container_number: string;
  container_size: string;
  container_size_display: string;
  container_status: string;
  container_status_display: string;
  period_start: string;
  period_end: string;
  is_still_on_terminal: boolean;
  total_days: number;
  free_days: number;
  billable_days: number;
  daily_rate_usd: string;
  daily_rate_uzs: string;
  amount_usd: string;
  amount_uzs: string;
}

interface StatementSummary {
  total_containers: number;
  total_billable_days: number;
  total_usd: string;
  total_uzs: string;
}

interface MonthlyStatement {
  id: number;
  year: number;
  month: number;
  month_name: string;
  billing_method: string;
  billing_method_display: string;
  summary: StatementSummary;
  line_items: StatementLineItem[];
  generated_at: string;
}

interface AvailablePeriod {
  year: number;
  month: number;
  label: string;
  has_statement: boolean;
}

const loading = ref(false);
const regenerating = ref(false);
const periodsLoading = ref(false);
const statement = ref<MonthlyStatement | null>(null);
const availablePeriods = ref<AvailablePeriod[]>([]);
const selectedYear = ref<number | null>(null);
const selectedMonth = ref<number | null>(null);

const availableYears = computed(() => {
  const years = new Set(availablePeriods.value.map(p => p.year));
  return Array.from(years).sort((a, b) => b - a);
});

const filteredMonths = computed(() => {
  if (!selectedYear.value) return availablePeriods.value;
  return availablePeriods.value.filter(p => p.year === selectedYear.value);
});

const columns: TableProps['columns'] = [
  { title: 'Контейнер', key: 'container', width: 150, fixed: 'left' },
  { title: 'Период', key: 'period', width: 140 },
  { title: 'Дни', key: 'days', width: 200 },
  { title: 'Ставка', key: 'rate', width: 100, align: 'right' },
  { title: 'Сумма USD', key: 'amount_usd', width: 120, align: 'right' },
  { title: 'Сумма UZS', key: 'amount_uzs', width: 150, align: 'right' },
];

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('ru-RU');
};

const formatDateTime = (dateStr: string): string => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('ru-RU');
};

const formatCurrency = (value: string, currency: 'USD' | 'UZS'): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  if (currency === 'USD') {
    return `$${num.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}`;
  }
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0 })} сум`;
};

const formatUzs = (value: string): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0 })} сум`;
};

const fetchAvailablePeriods = async () => {
  periodsLoading.value = true;
  try {
    const result = await http.get<{ success: boolean; data: AvailablePeriod[] }>(
      '/customer/billing/available-periods/'
    );
    availablePeriods.value = result.data || [];

    // Auto-select most recent period
    if (availablePeriods.value.length > 0) {
      const first = availablePeriods.value[0];
      selectedYear.value = first.year;
      selectedMonth.value = first.month;
    }
  } catch (error) {
    console.error('Error fetching periods:', error);
    message.error('Не удалось загрузить доступные периоды');
  } finally {
    periodsLoading.value = false;
  }
};

const handlePeriodChange = () => {
  statement.value = null;
};

const fetchStatement = async (regenerate = false) => {
  if (!selectedYear.value || !selectedMonth.value) return;

  loading.value = true;
  if (regenerate) regenerating.value = true;

  try {
    const url = `/customer/billing/statements/${selectedYear.value}/${selectedMonth.value}/${regenerate ? '?regenerate=true' : ''}`;
    const result = await http.get<{ success: boolean; data: MonthlyStatement }>(url);
    statement.value = result.data;

    if (regenerate) {
      message.success('Выписка пересчитана');
    }

    // Update available periods to show has_statement
    await fetchAvailablePeriods();
  } catch (error) {
    console.error('Error fetching statement:', error);
    message.error('Не удалось загрузить выписку');
  } finally {
    loading.value = false;
    regenerating.value = false;
  }
};

const regenerateStatement = () => fetchStatement(true);

const exportExcel = () => {
  if (!selectedYear.value || !selectedMonth.value) return;
  window.open(
    `/api/customer/billing/statements/${selectedYear.value}/${selectedMonth.value}/export/excel/`,
    '_blank'
  );
  message.success('Загрузка Excel начата');
};

const exportPdf = () => {
  if (!selectedYear.value || !selectedMonth.value) return;
  window.open(
    `/api/customer/billing/statements/${selectedYear.value}/${selectedMonth.value}/export/pdf/`,
    '_blank'
  );
  message.success('Загрузка PDF начата');
};

onMounted(() => {
  fetchAvailablePeriods();
});
</script>

<style scoped>
.monthly-statements {
  padding: 8px 0;
}

.period-end {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.days-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.amount-usd {
  font-weight: 600;
  color: #52c41a;
}

.amount-uzs {
  font-weight: 500;
  color: #722ed1;
}
</style>
```

**Step 4: Update router**

Modify `frontend/src/router/index.ts`:

Replace import and route for StorageCosts:

```typescript
// Change this import:
import CustomerStorageCosts from '../views/customer/StorageCosts.vue';
// To:
import CustomerBilling from '../views/customer/Billing.vue';

// Change the route (around line 99-103):
// From:
{
  path: 'storage-costs',
  name: 'CustomerStorageCosts',
  component: CustomerStorageCosts,
  meta: { title: 'Стоимость хранения - МТТ', roles: ['customer'] as UserRole[] },
},
// To:
{
  path: 'billing',
  name: 'CustomerBilling',
  component: CustomerBilling,
  meta: { title: 'Биллинг - МТТ', roles: ['customer'] as UserRole[] },
},
```

**Step 5: Update CustomerLayout tabs**

Modify `frontend/src/layouts/CustomerLayout.vue`:

Change the tab configuration (around line 40):

```vue
<!-- Change from: -->
<a-tab-pane key="storage-costs" tab="Стоимость хранения" />
<!-- To: -->
<a-tab-pane key="billing" tab="Биллинг" />
```

Update the helper function and route mapping:

```typescript
// In getTabFromRoute function:
if (routeName?.includes('Billing')) return 'billing';

// In tabRoutes object:
const tabRoutes: Record<string, string> = {
  dashboard: '/customer/dashboard',
  containers: '/customer/containers',
  billing: '/customer/billing',  // Changed from 'storage-costs'
  orders: '/customer/orders',
  users: '/customer/users',
};
```

**Step 6: Build and verify**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no TypeScript errors

**Step 7: Commit**

```bash
git add frontend/src/views/customer/Billing.vue frontend/src/components/billing/ frontend/src/router/index.ts frontend/src/layouts/CustomerLayout.vue
git rm frontend/src/views/customer/StorageCosts.vue
git commit -m "feat(frontend): transform Storage Costs into tabbed Billing page

Replaces Storage Costs page with comprehensive Billing page:
- Tab 1: Current Costs (existing functionality)
- Tab 2: Monthly Statements with period selection

Features:
- Year/month dropdowns populated from available periods
- Statement generation and regeneration
- Excel and PDF export buttons
- Detailed line items table with all cost information

Updates navigation from 'Стоимость хранения' to 'Биллинг'."
```

---

## Task 7: Final Testing and Cleanup

**Step 1: Run all backend tests**

```bash
cd backend && pytest tests/billing/ -v
```

**Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

**Step 3: Manual testing checklist**

- [ ] Navigate to `/customer/billing`
- [ ] Verify "Текущие расходы" tab shows existing costs
- [ ] Verify "Ежемесячные счета" tab loads periods
- [ ] Select a period and click "Показать"
- [ ] Verify statement summary and line items display
- [ ] Click "Пересчитать" and verify regeneration
- [ ] Click Excel export and verify download
- [ ] Click PDF export and verify download
- [ ] Test with different billing methods (split/exit_month)

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(billing): complete customer billing and monthly statements feature

Summary:
- Added billing_method field to Company model (split/exit_month)
- Created MonthlyStatement and StatementLineItem models
- Implemented MonthlyStatementService with hybrid generation
- Added customer API endpoints for statements
- Created Excel and PDF export functionality
- Built tabbed Billing page with Current Costs and Monthly Statements

Closes: Customer billing transparency feature"
```

---

## Summary

| Task | Files Created/Modified | Commit Message |
|------|----------------------|----------------|
| 1 | accounts/models.py, migration | feat(billing): add billing_method field to Company |
| 2 | billing/models.py, migration | feat(billing): add MonthlyStatement and StatementLineItem |
| 3 | billing/services/statement_service.py | feat(billing): add MonthlyStatementService |
| 4 | billing/views.py, urls.py, serializers.py | feat(billing): add customer statement API endpoints |
| 5 | billing/services/export_service.py, templates/ | feat(billing): add Excel and PDF export |
| 6 | frontend views, components, router | feat(frontend): transform Storage Costs into Billing page |
| 7 | - | feat(billing): complete customer billing feature |

**Total estimated time:** 4-6 hours
