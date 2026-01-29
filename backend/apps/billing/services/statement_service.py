"""
Monthly statement generation service.

This service handles the generation and management of monthly billing statements.
It reuses StorageCostService for all cost calculations to avoid duplication.

Lifecycle: draft → finalized → paid (with credit notes for corrections).
"""

import decimal
from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.db.models import Max, Q, QuerySet
from django.utils import timezone

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import (
    MonthlyStatement,
    StatementLineItem,
    StatementServiceItem,
    StatementStatus,
    StatementType,
    Tariff,
)
from .storage_cost_service import StorageCostService


if TYPE_CHECKING:
    from apps.accounts.models import Company, CustomUser
    from apps.terminal_operations.models import ContainerEntry


class MonthlyStatementService(BaseService):
    """
    Service for generating and managing monthly billing statements.

    Lifecycle:
    - draft: Auto-generated or manually created, can be regenerated
    - finalized: Locked, invoice number assigned, immutable
    - paid: Payment recorded
    - cancelled: Reversed by credit note

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

    # ── Statement generation ──────────────────────────────────────

    def get_or_generate_statement(
        self,
        company: "Company",
        year: int,
        month: int,
        user: "CustomUser | None" = None,
        regenerate: bool = False,
    ) -> MonthlyStatement:
        """
        Get existing statement or generate a new draft.

        Regeneration is only allowed for draft statements.
        """
        existing = MonthlyStatement.objects.filter(
            company=company, year=year, month=month, statement_type=StatementType.INVOICE,
        ).first()

        if existing and not regenerate:
            return existing

        if existing and not existing.is_editable:
            raise BusinessLogicError(
                "Невозможно пересчитать утверждённый документ. Используйте корректировку.",
                code="STATEMENT_NOT_EDITABLE",
            )

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
        """Core statement generation logic."""
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

        # Delete existing items if regenerating
        if existing:
            existing.line_items.all().delete()
            existing.service_items.all().delete()
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
                status=StatementStatus.DRAFT,
                statement_type=StatementType.INVOICE,
            )
            statement.save()

        # Generate storage line items
        total_storage_usd = Decimal("0.00")
        total_storage_uzs = Decimal("0.00")
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
                    total_storage_usd += line_item.amount_usd
                    total_storage_uzs += line_item.amount_uzs
                    total_billable_days += line_item.billable_days
                    line_items_created += 1
            except (Tariff.DoesNotExist, ValueError, decimal.InvalidOperation) as e:
                self.logger.warning(f"Failed to create line item for entry {entry.id}: {e}")
                continue

        # Generate service items from additional charges
        total_services_usd, total_services_uzs = self._create_service_items(
            statement, company, month_start, month_end
        )

        # Generate pending containers snapshot (for exit_month billing)
        pending_data = None
        if billing_method == BillingMethod.EXIT_MONTH:
            pending_data = self._build_pending_containers_snapshot(company, month_end)

        # Update statement totals
        statement.total_containers = line_items_created
        statement.total_billable_days = total_billable_days
        statement.total_storage_usd = total_storage_usd
        statement.total_storage_uzs = total_storage_uzs
        statement.total_services_usd = total_services_usd
        statement.total_services_uzs = total_services_uzs
        statement.total_usd = total_storage_usd + total_services_usd
        statement.total_uzs = total_storage_uzs + total_services_uzs
        statement.pending_containers_data = pending_data
        statement.save()

        self.logger.info(
            f"Generated statement {statement.id}: {line_items_created} containers, "
            f"storage=${total_storage_usd}, services=${total_services_usd}"
        )

        return statement

    def _create_service_items(
        self,
        statement: MonthlyStatement,
        company: "Company",
        month_start: date,
        month_end: date,
    ) -> tuple[Decimal, Decimal]:
        """Create service items from additional charges in the month."""
        from ..models import AdditionalCharge

        charges = AdditionalCharge.objects.filter(
            container_entry__company=company,
            charge_date__gte=month_start,
            charge_date__lte=month_end,
        ).select_related("container_entry__container")

        total_usd = Decimal("0.00")
        total_uzs = Decimal("0.00")

        for charge in charges:
            container_number = ""
            if charge.container_entry and charge.container_entry.container:
                container_number = charge.container_entry.container.container_number

            StatementServiceItem.objects.create(
                statement=statement,
                additional_charge=charge,
                container_number=container_number,
                description=charge.description,
                charge_date=charge.charge_date,
                amount_usd=charge.amount_usd,
                amount_uzs=charge.amount_uzs,
            )
            total_usd += charge.amount_usd
            total_uzs += charge.amount_uzs

        return total_usd, total_uzs

    def _build_pending_containers_snapshot(
        self,
        company: "Company",
        month_end: date,
    ) -> list[dict] | None:
        """Build snapshot of containers still on terminal (for exit_month billing)."""
        from apps.terminal_operations.models import ContainerEntry

        pending_entries = ContainerEntry.objects.filter(
            company=company,
            entry_time__date__lte=month_end,
            exit_date__isnull=True,
        ).select_related("container")

        if not pending_entries.exists():
            return None

        snapshot = []
        for entry in pending_entries:
            try:
                cost = self.storage_cost_service.calculate_cost(entry)
                snapshot.append({
                    "container_number": cost.container_number,
                    "container_size": cost.container_size,
                    "entry_date": cost.entry_date.isoformat(),
                    "days_so_far": cost.total_days,
                    "estimated_usd": str(cost.total_usd),
                    "estimated_uzs": str(cost.total_uzs),
                })
            except (Tariff.DoesNotExist, ValueError, decimal.InvalidOperation) as e:
                self.logger.warning(f"Failed to calculate pending cost for entry {entry.id}: {e}")

        return snapshot if snapshot else None

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

        cost_result = self.storage_cost_service.calculate_cost(entry)

        if billing_method == BillingMethod.SPLIT:
            period_start = max(cost_result.entry_date, month_start)
            period_end = min(cost_result.end_date, month_end)

            if period_start > period_end:
                return None

            total_days = (period_end - period_start).days + 1
            full_days = cost_result.total_days
            if full_days > 0:
                ratio = Decimal(total_days) / Decimal(full_days)
                amount_usd = (cost_result.total_usd * ratio).quantize(Decimal("0.01"))
                amount_uzs = (cost_result.total_uzs * ratio).quantize(Decimal("0.01"))
                free_days = min(cost_result.free_days_applied, total_days)
                billable_days = total_days - free_days
            else:
                amount_usd = Decimal("0.00")
                amount_uzs = Decimal("0.00")
                free_days = 0
                billable_days = 0
        else:
            period_start = cost_result.entry_date
            period_end = cost_result.end_date
            total_days = cost_result.total_days
            free_days = cost_result.free_days_applied
            billable_days = cost_result.billable_days
            amount_usd = cost_result.total_usd
            amount_uzs = cost_result.total_uzs

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

    # ── Lifecycle actions ─────────────────────────────────────────

    def finalize_statement(
        self,
        statement: MonthlyStatement,
        user: "CustomUser",
        _retries: int = 3,
    ) -> MonthlyStatement:
        """
        Finalize a draft statement.

        Assigns an invoice number and locks the statement.
        Retries on duplicate invoice number (concurrent finalization).
        """
        if statement.status != StatementStatus.DRAFT:
            raise BusinessLogicError(
                "Только черновики можно утвердить",
                code="INVALID_STATUS_TRANSITION",
            )

        for attempt in range(_retries):
            try:
                with transaction.atomic():
                    invoice_number = self._get_next_invoice_number(
                        statement.year, statement.statement_type
                    )

                    statement.status = StatementStatus.FINALIZED
                    statement.invoice_number = invoice_number
                    statement.finalized_at = timezone.now()
                    statement.finalized_by = user
                    statement.save(update_fields=[
                        "status", "invoice_number", "finalized_at", "finalized_by",
                    ])

                    self.logger.info(
                        f"Finalized statement {statement.id} as {invoice_number} by {user}"
                    )
                    return statement
            except IntegrityError:
                if attempt == _retries - 1:
                    raise
                self.logger.warning(
                    f"Invoice number collision on attempt {attempt + 1}, retrying"
                )
                statement.refresh_from_db()

        raise BusinessLogicError(
            "Не удалось сгенерировать номер документа",
            code="INVOICE_NUMBER_GENERATION_FAILED",
        )

    def mark_paid(
        self,
        statement: MonthlyStatement,
        user: "CustomUser",
    ) -> MonthlyStatement:
        """Toggle payment status on a finalized statement."""
        if statement.status == StatementStatus.PAID:
            statement.status = StatementStatus.FINALIZED
            statement.paid_at = None
            statement.paid_marked_by = None
        elif statement.status == StatementStatus.FINALIZED:
            statement.status = StatementStatus.PAID
            statement.paid_at = timezone.now()
            statement.paid_marked_by = user
        else:
            raise BusinessLogicError(
                "Отметить оплату можно только для утверждённых документов",
                code="INVALID_STATUS_TRANSITION",
            )

        statement.save(update_fields=["status", "paid_at", "paid_marked_by"])
        self.logger.info(
            f"Statement {statement.id} marked as {statement.status} by {user}"
        )
        return statement

    @transaction.atomic
    def create_credit_note(
        self,
        original: MonthlyStatement,
        user: "CustomUser",
    ) -> MonthlyStatement:
        """
        Create a credit note that reverses the original statement.

        The credit note contains negative amounts matching the original.
        The original statement is marked as cancelled.
        """
        if original.status not in (StatementStatus.FINALIZED, StatementStatus.PAID):
            raise BusinessLogicError(
                "Корректировку можно создать только для утверждённых или оплаченных документов",
                code="INVALID_STATUS_TRANSITION",
            )

        # Create credit note
        credit_note = MonthlyStatement.objects.create(
            company=original.company,
            year=original.year,
            month=original.month,
            billing_method=original.billing_method,
            statement_type=StatementType.CREDIT_NOTE,
            status=StatementStatus.DRAFT,
            original_statement=original,
            generated_by=user,
            total_containers=original.total_containers,
            total_billable_days=original.total_billable_days,
            total_storage_usd=-original.total_storage_usd,
            total_storage_uzs=-original.total_storage_uzs,
            total_services_usd=-original.total_services_usd,
            total_services_uzs=-original.total_services_uzs,
            total_usd=-original.total_usd,
            total_uzs=-original.total_uzs,
        )

        # Copy line items with negative amounts
        for item in original.line_items.all():
            StatementLineItem.objects.create(
                statement=credit_note,
                container_entry=item.container_entry,
                container_number=item.container_number,
                container_size=item.container_size,
                container_status=item.container_status,
                period_start=item.period_start,
                period_end=item.period_end,
                is_still_on_terminal=item.is_still_on_terminal,
                total_days=item.total_days,
                free_days=item.free_days,
                billable_days=item.billable_days,
                daily_rate_usd=item.daily_rate_usd,
                daily_rate_uzs=item.daily_rate_uzs,
                amount_usd=-item.amount_usd,
                amount_uzs=-item.amount_uzs,
            )

        # Copy service items with negative amounts
        for svc in original.service_items.all():
            StatementServiceItem.objects.create(
                statement=credit_note,
                additional_charge=svc.additional_charge,
                container_number=svc.container_number,
                description=svc.description,
                charge_date=svc.charge_date,
                amount_usd=-svc.amount_usd,
                amount_uzs=-svc.amount_uzs,
            )

        # Mark original as cancelled
        original.status = StatementStatus.CANCELLED
        original.save(update_fields=["status"])

        self.logger.info(
            f"Created credit note {credit_note.id} for statement {original.id}"
        )
        return credit_note

    # ── Invoice numbering ─────────────────────────────────────────

    def _get_next_invoice_number(self, year: int, statement_type: str) -> str:
        """Generate the next sequential invoice number for the year.

        Uses select_for_update to prevent race conditions when
        two statements are finalized concurrently.
        """
        if statement_type == StatementType.CREDIT_NOTE:
            prefix = f"MTT-CR-{year}-"
        else:
            prefix = f"MTT-{year}-"

        last = (
            MonthlyStatement.objects
            .select_for_update()
            .filter(invoice_number__startswith=prefix)
            .aggregate(max_num=Max("invoice_number"))
        )["max_num"]

        if last:
            last_seq = int(last.split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:04d}"

    # ── Bulk generation ───────────────────────────────────────────

    @transaction.atomic
    def generate_all_drafts(
        self,
        year: int,
        month: int,
        user: "CustomUser | None" = None,
    ) -> list[MonthlyStatement]:
        """Generate draft statements for all companies with activity in the period."""
        from apps.accounts.models import Company
        from apps.terminal_operations.models import ContainerEntry

        month_start, month_end = self._get_month_boundaries(year, month)

        # Find companies with container activity in this month
        company_ids = (
            ContainerEntry.objects.filter(
                entry_time__date__lte=month_end,
            )
            .filter(Q(exit_date__isnull=True) | Q(exit_date__date__gte=month_start))
            .values_list("company_id", flat=True)
            .distinct()
        )

        # Exclude companies that already have an invoice for this month
        existing = set(
            MonthlyStatement.objects.filter(
                year=year, month=month, statement_type=StatementType.INVOICE,
            ).values_list("company_id", flat=True)
        )

        companies = Company.objects.filter(id__in=company_ids).exclude(id__in=existing)

        statements = []
        for company in companies:
            try:
                stmt = self._generate_statement(company, year, month, user, None)
                statements.append(stmt)
            except Exception as e:
                self.logger.warning(
                    f"Failed to generate statement for {company.name}: {e}"
                )

        self.logger.info(
            f"Bulk generated {len(statements)} draft statements for {year}/{month}"
        )
        return statements

    # ── Queries ────────────────────────────────────────────────────

    def list_statements(
        self,
        company: "Company",
        year: int | None = None,
    ) -> QuerySet[MonthlyStatement]:
        """List all statements for a company, optionally filtered by year."""
        queryset = MonthlyStatement.objects.filter(
            company=company
        ).select_related("paid_marked_by", "finalized_by", "original_statement")
        if year:
            queryset = queryset.filter(year=year)
        return queryset

    def get_available_periods(
        self,
        company: "Company",
    ) -> list[dict]:
        """Returns months with container activity for dropdown."""
        from apps.terminal_operations.models import ContainerEntry

        entries = ContainerEntry.objects.filter(company=company).values_list(
            "entry_time", flat=True
        )

        existing_statements = set(
            MonthlyStatement.objects.filter(
                company=company, statement_type=StatementType.INVOICE,
            ).values_list("year", "month")
        )

        periods_set = set()
        for entry_time in entries:
            if entry_time:
                periods_set.add((entry_time.year, entry_time.month))

        periods = []
        for year, month in sorted(periods_set, reverse=True):
            periods.append({
                "year": year,
                "month": month,
                "label": f"{self.MONTH_NAMES[month - 1]} {year}",
                "has_statement": (year, month) in existing_statements,
            })

        return periods

    @transaction.atomic
    def delete_statement(self, statement: MonthlyStatement) -> None:
        """Delete a draft statement."""
        if not statement.is_editable:
            raise BusinessLogicError(
                "Невозможно удалить утверждённый документ",
                code="STATEMENT_NOT_EDITABLE",
            )
        statement_id = statement.id
        statement.delete()
        self.logger.info(f"Deleted statement {statement_id}")

    # ── Helpers ────────────────────────────────────────────────────

    def _get_containers_for_split_billing(
        self,
        company: "Company",
        month_start: date,
        month_end: date,
    ) -> QuerySet["ContainerEntry"]:
        """Find containers active during any part of the month."""
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
