"""
On-demand invoice service.

Handles creating, finalizing, and managing on-demand invoices
for specific containers when customers request immediate billing.
Both active and exited containers are supported.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import (
    AdditionalCharge,
    OnDemandInvoice,
    OnDemandInvoiceItem,
    OnDemandInvoiceServiceItem,
    StatementStatus,
)
from .storage_cost_service import StorageCostService

if TYPE_CHECKING:
    from apps.accounts.models import Company, CustomUser


class OnDemandInvoiceService(BaseService):
    """Service for managing on-demand invoices."""

    def __init__(self):
        super().__init__()
        self.cost_service = StorageCostService()

    @transaction.atomic
    def create_invoice(
        self,
        company: "Company",
        container_entry_ids: list[int],
        user: "CustomUser",
        notes: str = "",
    ) -> OnDemandInvoice:
        """
        Create an on-demand invoice for specific containers.

        Validates that all entries belong to the company and are not
        already included in another on-demand invoice. Both active
        and exited containers are supported.
        """
        from apps.terminal_operations.models import ContainerEntry

        if not container_entry_ids:
            raise BusinessLogicError(
                "Необходимо выбрать хотя бы один контейнер",
                error_code="NO_CONTAINERS_SELECTED",
            )

        # select_for_update prevents race condition where two concurrent
        # requests could invoice the same container simultaneously.
        # Use of=("self",) to only lock ContainerEntry rows, avoiding
        # PostgreSQL error with nullable FK joins (container_owner, recorded_by).
        entries = ContainerEntry.objects.select_for_update(of=("self",)).filter(
            id__in=container_entry_ids,
        ).select_related("container", "company")

        # Validate all entries exist
        found_ids = set(entries.values_list("id", flat=True))
        missing_ids = set(container_entry_ids) - found_ids
        if missing_ids:
            raise BusinessLogicError(
                f"Записи контейнеров не найдены: {missing_ids}",
                error_code="ENTRIES_NOT_FOUND",
            )

        for entry in entries:
            # Validate company ownership
            if entry.company_id != company.id:
                raise BusinessLogicError(
                    f"Контейнер {entry.container.container_number} не принадлежит данной компании",
                    error_code="WRONG_COMPANY",
                )

            # Validate not already in an active on-demand invoice
            existing = entry.on_demand_items.filter(
                invoice__status__in=[
                    StatementStatus.DRAFT,
                    StatementStatus.FINALIZED,
                    StatementStatus.PAID,
                ],
            ).select_related("invoice").first()

            if existing:
                invoice_ref = existing.invoice.invoice_number or f"OD-DRAFT-{existing.invoice.id}"
                raise BusinessLogicError(
                    f"Контейнер {entry.container.container_number} уже включён в счёт {invoice_ref}",
                    error_code="ALREADY_INVOICED",
                )

        # Calculate costs and create invoice
        invoice = OnDemandInvoice.objects.create(
            company=company,
            status=StatementStatus.DRAFT,
            notes=notes,
            created_by=user,
        )

        total_usd = Decimal("0.00")
        total_uzs = Decimal("0.00")

        for entry in entries:
            cost = self.cost_service.calculate_cost(entry)

            OnDemandInvoiceItem.objects.create(
                invoice=invoice,
                container_entry=entry,
                container_number=cost.container_number,
                container_size=cost.container_size,
                container_status=cost.container_status,
                entry_date=cost.entry_date,
                exit_date=cost.end_date if not cost.is_active else None,
                total_days=cost.total_days,
                free_days=cost.free_days_applied,
                billable_days=cost.billable_days,
                daily_rate_usd=cost.periods[0].daily_rate_usd if cost.periods else Decimal("0"),
                daily_rate_uzs=cost.periods[0].daily_rate_uzs if cost.periods else Decimal("0"),
                amount_usd=cost.total_usd,
                amount_uzs=cost.total_uzs,
            )

            total_usd += cost.total_usd
            total_uzs += cost.total_uzs

        # Snapshot additional charges for the selected containers
        # Exclude charges already billed in non-cancelled monthly statements
        charges = AdditionalCharge.objects.filter(
            container_entry_id__in=container_entry_ids,
        ).exclude(
            # Exclude charges already billed in non-cancelled monthly statements
            statement_service_items__statement__status__in=[
                StatementStatus.DRAFT,
                StatementStatus.FINALIZED,
                StatementStatus.PAID,
            ]
        ).exclude(
            # Exclude charges already billed in non-cancelled on-demand invoices
            on_demand_service_items__invoice__status__in=[
                StatementStatus.DRAFT,
                StatementStatus.FINALIZED,
                StatementStatus.PAID,
            ]
        ).select_related("container_entry__container")

        services_usd = Decimal("0.00")
        services_uzs = Decimal("0.00")

        for charge in charges:
            OnDemandInvoiceServiceItem.objects.create(
                invoice=invoice,
                additional_charge=charge,
                container_number=charge.container_entry.container.container_number,
                description=charge.description,
                charge_date=charge.charge_date,
                amount_usd=charge.amount_usd,
                amount_uzs=charge.amount_uzs,
            )
            services_usd += charge.amount_usd
            services_uzs += charge.amount_uzs

        container_count = entries.count()
        invoice.total_containers = container_count
        invoice.total_usd = total_usd + services_usd
        invoice.total_uzs = total_uzs + services_uzs
        invoice.save(update_fields=["total_containers", "total_usd", "total_uzs"])

        self.logger.info(
            f"Created on-demand invoice {invoice.id} for {company.name}: "
            f"{container_count} containers, {charges.count()} services, "
            f"${invoice.total_usd} / {invoice.total_uzs} UZS"
        )

        return invoice

    def finalize_invoice(
        self,
        invoice: OnDemandInvoice,
        user: "CustomUser",
        _retries: int = 3,
    ) -> OnDemandInvoice:
        """Finalize a draft invoice, assigning an invoice number."""
        if invoice.status != StatementStatus.DRAFT:
            raise BusinessLogicError(
                "Только черновики можно утвердить",
                error_code="INVALID_STATUS_TRANSITION",
            )

        for attempt in range(_retries):
            try:
                with transaction.atomic():
                    invoice_number = self._get_next_invoice_number(
                        invoice.created_at.year
                    )
                    invoice.status = StatementStatus.FINALIZED
                    invoice.invoice_number = invoice_number
                    invoice.finalized_at = timezone.now()
                    invoice.finalized_by = user
                    invoice.save(update_fields=[
                        "status", "invoice_number", "finalized_at", "finalized_by",
                    ])

                    self.logger.info(
                        f"Finalized on-demand invoice {invoice.id} as {invoice_number}"
                    )
                    return invoice
            except IntegrityError:
                if attempt == _retries - 1:
                    raise
                self.logger.warning(
                    f"Invoice number collision on attempt {attempt + 1}, retrying"
                )
                invoice.refresh_from_db()

        # Unreachable in practice: the last attempt either returns or re-raises
        raise BusinessLogicError(
            "Не удалось сгенерировать номер документа",
            error_code="INVOICE_NUMBER_GENERATION_FAILED",
        )

    @transaction.atomic
    def mark_paid(
        self,
        invoice: OnDemandInvoice,
        user: "CustomUser",
        payment_reference: str = "",
        payment_date: "date | None" = None,
    ) -> OnDemandInvoice:
        """Toggle payment status between finalized and paid."""
        from datetime import date

        if invoice.status == StatementStatus.PAID:
            # Unmark as paid
            invoice.status = StatementStatus.FINALIZED
            invoice.paid_at = None
            invoice.paid_marked_by = None
            invoice.payment_reference = ""
            invoice.payment_date = None
            self.logger.info(f"Unmarked on-demand invoice {invoice.id} as paid")
        elif invoice.status == StatementStatus.FINALIZED:
            # Mark as paid with optional reference
            invoice.status = StatementStatus.PAID
            invoice.paid_at = timezone.now()
            invoice.paid_marked_by = user
            invoice.payment_reference = payment_reference or ""
            invoice.payment_date = payment_date or date.today()
            self.logger.info(f"Marked on-demand invoice {invoice.id} as paid")
        else:
            raise BusinessLogicError(
                "Отметить оплату можно только для утверждённых счетов",
                error_code="INVALID_STATUS_TRANSITION",
            )

        invoice.save(update_fields=[
            "status", "paid_at", "paid_marked_by",
            "payment_reference", "payment_date",
        ])
        return invoice

    @transaction.atomic
    def delete_invoice(
        self,
        invoice: OnDemandInvoice,
        user: "CustomUser",
    ) -> None:
        """Delete a draft invoice entirely (hard delete)."""
        if invoice.status != StatementStatus.DRAFT:
            raise BusinessLogicError(
                "Удалить можно только черновики. Для отмены утверждённого счёта используйте отмену.",
                error_code="CANNOT_DELETE_NON_DRAFT",
            )

        invoice_id = invoice.id
        company_name = invoice.company.name
        invoice.delete()

        self.logger.info(
            f"Deleted draft on-demand invoice {invoice_id} for {company_name} by {user}"
        )

    @transaction.atomic
    def cancel_invoice(
        self,
        invoice: OnDemandInvoice,
        user: "CustomUser",
        reason: str = "",
    ) -> OnDemandInvoice:
        """Cancel an invoice, releasing containers back to the monthly billing pool."""
        if invoice.status == StatementStatus.CANCELLED:
            raise BusinessLogicError(
                "Счёт уже отменён",
                error_code="ALREADY_CANCELLED",
            )

        if invoice.status == StatementStatus.PAID:
            raise BusinessLogicError(
                "Нельзя отменить оплаченный счёт",
                error_code="CANNOT_CANCEL_PAID",
            )

        # Finalized invoices require a cancellation reason
        if invoice.status == StatementStatus.FINALIZED:
            if not reason.strip():
                raise BusinessLogicError(
                    "Укажите причину отмены утверждённого счёта",
                    error_code="CANCELLATION_REASON_REQUIRED",
                )

        invoice.status = StatementStatus.CANCELLED
        invoice.cancelled_at = timezone.now()
        invoice.cancelled_by = user
        invoice.cancellation_reason = reason.strip()
        invoice.save(update_fields=[
            "status", "cancelled_at", "cancelled_by", "cancellation_reason"
        ])

        # Collect affected container numbers for the log message
        affected_containers = list(
            invoice.items.values_list("container_number", flat=True)
        )

        self.logger.info(
            f"Cancelled on-demand invoice {invoice.id} by {user}, "
            f"released {invoice.total_containers} containers, reason: {reason[:50]}"
        )
        self.logger.warning(
            f"Containers from cancelled invoice {invoice.id} are now eligible "
            f"for monthly billing: {affected_containers}. "
            f"Regenerate affected monthly statements to include them."
        )
        return invoice

    def list_invoices(
        self,
        company: "Company",
        status: str | None = None,
    ):
        """List on-demand invoices for a company, optionally filtered by status."""
        from django.db.models import Count, Q

        qs = (
            OnDemandInvoice.objects.filter(company=company)
            .select_related(
                "company", "created_by", "finalized_by",
                "paid_marked_by", "cancelled_by",
            )
            .prefetch_related("items", "service_items")
            .annotate(
                _pending_exit_count=Count(
                    "items",
                    filter=Q(items__exit_date__isnull=True),
                ),
            )
            .order_by("-created_at")
        )
        if status:
            qs = qs.filter(status=status)
        return qs

    def _get_next_invoice_number(self, year: int) -> str:
        """Generate the next sequential on-demand invoice number.

        Locks matching rows with select_for_update() before reading the max
        invoice number.  Note: select_for_update() is silently ignored when
        combined with .aggregate(), so we lock the rows first and then
        aggregate separately to guarantee serialized access.
        """
        prefix = f"OD-{year}-"

        # Lock all rows that could affect the next number.
        # IMPORTANT: select_for_update() is silently ignored when chained
        # with .aggregate() — Django drops the FOR UPDATE clause.  We must
        # evaluate the locking query first (which acquires row-level locks),
        # then compute the max via a separate aggregate call.
        list(
            OnDemandInvoice.objects
            .select_for_update()
            .filter(invoice_number__startswith=prefix)
            .values("id")
        )
        last = (
            OnDemandInvoice.objects
            .filter(invoice_number__startswith=prefix)
            .aggregate(max_num=Max("invoice_number"))
        )["max_num"]

        if last:
            last_seq = int(last.split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:04d}"
