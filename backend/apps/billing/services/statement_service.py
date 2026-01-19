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
