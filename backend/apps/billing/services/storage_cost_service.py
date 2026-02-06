"""
Storage cost calculation service.

This service handles the calculation of container storage costs based on:
- Container size (20ft/40ft derived from ISO type)
- Container status (laden/empty)
- Applicable tariffs (general or company-specific)
- Time periods (handles tariff changes mid-stay)
- Free days (locked at container entry time)
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import ContainerBillingStatus, ContainerSize, Tariff


if TYPE_CHECKING:
    from apps.terminal_operations.models import ContainerEntry


class TariffNotFoundError(BusinessLogicError):
    """Raised when no valid tariff is found for the given date and company."""

    def __init__(self, target_date: date, company_name: str | None = None):
        company_info = f" для компании '{company_name}'" if company_name else ""
        super().__init__(
            message=f"Тариф не найден на дату {target_date}{company_info}",
            error_code="TARIFF_NOT_FOUND",
            details={"date": str(target_date), "company": company_name},
        )


class TariffRateMissingError(BusinessLogicError):
    """Raised when a tariff exists but is missing a rate for the required size/status."""

    def __init__(
        self,
        target_date: date,
        container_size: str,
        container_status: str,
        company_name: str | None = None,
    ):
        size_display = "20 футов" if container_size == "20ft" else "40 футов"
        status_display = "груженый" if container_status == "laden" else "порожний"
        company_info = f" для компании '{company_name}'" if company_name else ""
        super().__init__(
            message=(
                f"Тариф на дату {target_date}{company_info} не содержит ставку "
                f"для контейнера {size_display}/{status_display}. "
                f"Необходимо добавить недостающую ставку в тариф."
            ),
            error_code="TARIFF_RATE_MISSING",
            details={
                "date": str(target_date),
                "company": company_name,
                "container_size": container_size,
                "container_status": container_status,
            },
        )


class InvalidContainerSizeError(BusinessLogicError):
    """Raised when container size cannot be determined from ISO type."""

    def __init__(self, iso_type: str):
        super().__init__(
            message=f"Невозможно определить размер контейнера по типу '{iso_type}'",
            error_code="INVALID_CONTAINER_SIZE",
            details={"iso_type": iso_type},
        )


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
    periods: list[StorageCostPeriod] = field(default_factory=list)

    # Metadata
    calculated_at: datetime = field(default_factory=timezone.now)


class StorageCostService(BaseService):
    """
    Service for calculating container storage costs.

    The calculation handles:
    1. Container size derivation from ISO type (first digit: 2=20ft, 4=40ft)
    2. Status mapping (LADEN→laden, EMPTY→empty)
    3. Tariff lookup with company-specific priority
    4. Period splitting when tariffs change mid-stay
    5. Free days locked at entry time
    """

    def calculate_cost(
        self,
        container_entry: "ContainerEntry",
        as_of_date: date | None = None,
    ) -> StorageCostResult:
        """
        Calculate storage cost for a container entry.

        Args:
            container_entry: The container to calculate cost for
            as_of_date: Calculate up to this date (default: today or exit_date)

        Returns:
            StorageCostResult with detailed breakdown

        Raises:
            TariffNotFoundError: If no valid tariff exists for any period
            InvalidContainerSizeError: If container size cannot be determined
        """
        # 1. Determine calculation dates
        entry_date = container_entry.entry_time.date()
        exit_date = (
            container_entry.exit_date.date() if container_entry.exit_date else None
        )

        # Determine end date for calculation
        if as_of_date:
            end_date = as_of_date
        elif exit_date:
            end_date = exit_date
        else:
            end_date = timezone.now().date()

        is_active = container_entry.exit_date is None

        # 2. Determine container properties
        container_size = self._derive_size_from_iso_type(
            container_entry.container.iso_type
        )
        container_status = self._map_entry_status(container_entry.status)
        company = container_entry.company

        self.logger.info(
            f"Calculating storage cost for {container_entry.container.container_number}: "
            f"size={container_size}, status={container_status}, "
            f"entry={entry_date}, end={end_date}, company={company}"
        )

        # 3. Initialize tracking variables
        periods: list[StorageCostPeriod] = []
        total_usd = Decimal("0.00")
        total_uzs = Decimal("0.00")
        free_days_remaining: int | None = None  # Set from first tariff
        initial_free_days = 0
        current_date = entry_date

        # 4. Process each tariff period
        while current_date <= end_date:
            # Find applicable tariff for this date
            tariff = self._get_applicable_tariff(company, current_date)
            rate = tariff.get_rate(container_size, container_status)

            if not rate:
                raise TariffRateMissingError(
                    target_date=current_date,
                    container_size=container_size,
                    container_status=container_status,
                    company_name=company.name if company else None,
                )

            # Set free days on first iteration (locked at entry)
            if free_days_remaining is None:
                free_days_remaining = rate.free_days
                initial_free_days = rate.free_days

            # Calculate period boundaries
            period_end = self._calculate_period_end(
                current_date=current_date,
                end_date=end_date,
                tariff=tariff,
                company=company,
            )

            days_in_period = (period_end - current_date).days + 1

            # Apply free days
            free_days_used = min(free_days_remaining, days_in_period)
            free_days_remaining -= free_days_used
            billable_days = days_in_period - free_days_used

            # Calculate amounts
            amount_usd = Decimal(billable_days) * rate.daily_rate_usd
            amount_uzs = Decimal(billable_days) * rate.daily_rate_uzs

            # Record period
            periods.append(
                StorageCostPeriod(
                    start_date=current_date,
                    end_date=period_end,
                    days=days_in_period,
                    free_days_used=free_days_used,
                    billable_days=billable_days,
                    tariff_id=tariff.id,
                    tariff_type="special" if tariff.company else "general",
                    daily_rate_usd=rate.daily_rate_usd,
                    daily_rate_uzs=rate.daily_rate_uzs,
                    amount_usd=amount_usd,
                    amount_uzs=amount_uzs,
                )
            )

            total_usd += amount_usd
            total_uzs += amount_uzs

            # Move to next period
            current_date = period_end + timedelta(days=1)

        # 5. Build and return result
        total_days = (end_date - entry_date).days + 1
        free_days_applied = initial_free_days - (free_days_remaining or 0)

        result = StorageCostResult(
            container_entry_id=container_entry.id,
            container_number=container_entry.container.container_number,
            company_name=company.name if company else None,
            container_size=container_size,
            container_status=container_status,
            entry_date=entry_date,
            end_date=end_date,
            is_active=is_active,
            total_days=total_days,
            free_days_applied=free_days_applied,
            billable_days=sum(p.billable_days for p in periods),
            total_usd=total_usd,
            total_uzs=total_uzs,
            periods=periods,
        )

        self.logger.info(
            f"Calculated storage cost: {total_usd} USD / {total_uzs} UZS "
            f"for {total_days} days ({free_days_applied} free)"
        )

        return result

    def calculate_bulk_costs(
        self,
        container_entries: QuerySet["ContainerEntry"],
        as_of_date: date | None = None,
    ) -> list[StorageCostResult]:
        """
        Calculate costs for multiple containers efficiently.

        Args:
            container_entries: QuerySet of container entries
            as_of_date: Calculate up to this date (default: today or each exit_date)

        Returns:
            List of StorageCostResult for each container
        """
        results = []

        # Prefetch related data for efficiency
        entries = container_entries.select_related("container", "company")

        for entry in entries:
            try:
                result = self.calculate_cost(entry, as_of_date)
                results.append(result)
            except (TariffNotFoundError, TariffRateMissingError, InvalidContainerSizeError) as e:
                self.logger.warning(
                    f"Failed to calculate cost for entry {entry.id}: {e}"
                )
                # Skip entries with calculation errors
                continue

        return results

    def _get_applicable_tariff(
        self,
        company,
        target_date: date,
    ) -> Tariff:
        """
        Find the tariff applicable for a company on a given date.

        Priority:
        1. Company-specific tariff valid on target_date
        2. General tariff (company=NULL) valid on target_date

        Args:
            company: Company instance or None
            target_date: The date to find tariff for

        Returns:
            Tariff instance

        Raises:
            TariffNotFoundError: If no valid tariff found
        """
        # Build date filter: effective_from <= target_date AND (effective_to IS NULL OR effective_to >= target_date)
        date_filter = Q(effective_from__lte=target_date) & (
            Q(effective_to__isnull=True) | Q(effective_to__gte=target_date)
        )

        # First try to find company-specific tariff
        if company:
            special_tariff = (
                Tariff.objects.filter(date_filter, company=company)
                .prefetch_related("rates")
                .order_by("-effective_from")
                .first()
            )
            if special_tariff:
                self.logger.debug(
                    f"Found special tariff {special_tariff.id} for {company.name}"
                )
                return special_tariff

        # Fall back to general tariff
        general_tariff = (
            Tariff.objects.filter(date_filter, company__isnull=True)
            .prefetch_related("rates")
            .order_by("-effective_from")
            .first()
        )

        if general_tariff:
            self.logger.debug(f"Using general tariff {general_tariff.id}")
            return general_tariff

        # No tariff found
        raise TariffNotFoundError(
            target_date,
            company.name if company else None,
        )

    def _calculate_period_end(
        self,
        current_date: date,
        end_date: date,
        tariff: Tariff,
        company,
    ) -> date:
        """
        Calculate when the current tariff period ends.

        The period ends at the earliest of:
        1. The container's end_date
        2. The tariff's effective_to date
        3. The day before the next tariff starts (special or general)

        Args:
            current_date: Start of current period
            end_date: Container's calculation end date
            tariff: Currently applicable tariff
            company: Company for looking up next tariffs

        Returns:
            End date for this period
        """
        candidates = [end_date]

        # Add tariff's effective_to if set
        if tariff.effective_to:
            candidates.append(tariff.effective_to)

        # Check if there's a newer tariff that starts during this period
        next_tariff_start = self._get_next_tariff_start(current_date, company, tariff)
        if next_tariff_start and next_tariff_start <= end_date:
            # Period ends the day before next tariff starts
            candidates.append(next_tariff_start - timedelta(days=1))

        return min(candidates)

    def _get_next_tariff_start(
        self,
        after_date: date,
        company,
        current_tariff: Tariff,
    ) -> date | None:
        """
        Find when the next tariff starts after a given date.

        This handles both:
        - New special tariff for the company
        - Special tariff expiring (falls back to general)
        - New general tariff (if no special exists)
        """
        # Look for tariffs starting after the current date
        candidates = []

        # Check for next company-specific tariff
        if company:
            next_special = (
                Tariff.objects.filter(
                    company=company,
                    effective_from__gt=after_date,
                )
                .order_by("effective_from")
                .first()
            )
            if next_special:
                candidates.append(next_special.effective_from)

            # If current is special and it expires, we need to switch to general
            if current_tariff.company and current_tariff.effective_to:
                # The day after expiry, we switch to general
                candidates.append(current_tariff.effective_to + timedelta(days=1))

        # Check for next general tariff (if we're using general)
        if not current_tariff.company:
            next_general = (
                Tariff.objects.filter(
                    company__isnull=True,
                    effective_from__gt=after_date,
                )
                .order_by("effective_from")
                .first()
            )
            if next_general:
                candidates.append(next_general.effective_from)

        return min(candidates) if candidates else None

    def _derive_size_from_iso_type(self, iso_type: str | None) -> str:
        """
        Derive container size from ISO type code.

        ISO codes starting with:
        - 2 (20, 22, 25, etc.) → 20ft
        - 4 (40, 42, 45, etc.) → 40ft
        - L (L5G1, etc.) → 40ft (45ft containers treated as 40ft for billing)

        Args:
            iso_type: ISO container type code

        Returns:
            ContainerSize value ('20ft' or '40ft')

        Raises:
            InvalidContainerSizeError: If size cannot be determined
        """
        if not iso_type:
            # Default to 20ft if no ISO type specified
            self.logger.warning("No ISO type provided, defaulting to 20ft")
            return ContainerSize.TWENTY_FT

        first_char = iso_type[0].upper()

        if first_char == "2":
            return ContainerSize.TWENTY_FT
        elif first_char in ("4", "L"):
            return ContainerSize.FORTY_FT
        else:
            raise InvalidContainerSizeError(iso_type)

    def _map_entry_status(self, entry_status: str) -> str:
        """
        Map ContainerEntry status to billing status.

        ContainerEntry uses: LADEN, EMPTY
        Billing uses: laden, empty

        Args:
            entry_status: Status from ContainerEntry model

        Returns:
            ContainerBillingStatus value
        """
        status_map = {
            "LADEN": ContainerBillingStatus.LADEN,
            "EMPTY": ContainerBillingStatus.EMPTY,
        }

        return status_map.get(entry_status, ContainerBillingStatus.LADEN)

    def get_active_tariff(self, company=None) -> Tariff | None:
        """
        Get the currently active tariff for a company (or general).

        Args:
            company: Company instance or None for general tariff

        Returns:
            Active Tariff or None if no active tariff exists
        """
        today = timezone.now().date()
        return self._get_applicable_tariff(company, today)

    def get_tariff_history(
        self,
        company=None,
        limit: int = 10,
    ) -> QuerySet[Tariff]:
        """
        Get tariff history for a company (or general tariffs).

        Args:
            company: Company instance or None for general tariffs
            limit: Maximum number of tariffs to return

        Returns:
            QuerySet of Tariff ordered by effective_from descending
        """
        queryset = Tariff.objects.filter(company=company).prefetch_related("rates")
        return queryset.order_by("-effective_from")[:limit]
