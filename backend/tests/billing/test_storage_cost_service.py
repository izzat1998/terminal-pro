"""
Tests for the Storage Cost Service.

Tests cover:
- Container size derivation from ISO type
- Status mapping
- Single period calculation
- Multi-period calculation (tariff changes)
- Free days handling (locked at entry)
- Special tariff priority
- Special tariff expiry
- Active container calculation
- Edge cases
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Company, CustomUser
from apps.billing.models import (
    ContainerBillingStatus,
    ContainerSize,
    Tariff,
    TariffRate,
)
from apps.billing.services.storage_cost_service import (
    InvalidContainerSizeError,
    StorageCostService,
    TariffNotFoundError,
)
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_user(db):
    """Create admin user for tests."""
    return CustomUser.objects.create_user(
        username="billing_test_admin",
        password="testpass123",
        user_type="admin",
        is_staff=True,
    )


@pytest.fixture
def test_company(db):
    """Create a test company."""
    return Company.objects.create(
        name="Test Logistics Co",
        slug="test-logistics",
    )


@pytest.fixture
def general_tariff(db, admin_user):
    """Create a general tariff with all rates."""
    tariff = Tariff.objects.create(
        company=None,  # General tariff
        effective_from=date(2025, 1, 1),
        effective_to=None,  # Active
        created_by=admin_user,
        notes="General tariff for testing",
    )

    # Create all 4 rate combinations
    rates_data = [
        (
            ContainerSize.TWENTY_FT,
            ContainerBillingStatus.LADEN,
            "10.00",
            "125000.00",
            5,
        ),
        (ContainerSize.TWENTY_FT, ContainerBillingStatus.EMPTY, "8.00", "100000.00", 5),
        (ContainerSize.FORTY_FT, ContainerBillingStatus.LADEN, "18.00", "225000.00", 5),
        (ContainerSize.FORTY_FT, ContainerBillingStatus.EMPTY, "15.00", "187500.00", 5),
    ]

    for size, status, usd, uzs, free_days in rates_data:
        TariffRate.objects.create(
            tariff=tariff,
            container_size=size,
            container_status=status,
            daily_rate_usd=Decimal(usd),
            daily_rate_uzs=Decimal(uzs),
            free_days=free_days,
        )

    return tariff


@pytest.fixture
def special_tariff(db, admin_user, test_company):
    """Create a special tariff for test company."""
    tariff = Tariff.objects.create(
        company=test_company,
        effective_from=date(2025, 1, 1),
        effective_to=None,
        created_by=admin_user,
        notes="Special tariff for Test Logistics",
    )

    # Discounted rates with more free days
    rates_data = [
        (ContainerSize.TWENTY_FT, ContainerBillingStatus.LADEN, "8.00", "100000.00", 7),
        (ContainerSize.TWENTY_FT, ContainerBillingStatus.EMPTY, "6.00", "75000.00", 7),
        (ContainerSize.FORTY_FT, ContainerBillingStatus.LADEN, "14.00", "175000.00", 7),
        (ContainerSize.FORTY_FT, ContainerBillingStatus.EMPTY, "12.00", "150000.00", 7),
    ]

    for size, status, usd, uzs, free_days in rates_data:
        TariffRate.objects.create(
            tariff=tariff,
            container_size=size,
            container_status=status,
            daily_rate_usd=Decimal(usd),
            daily_rate_uzs=Decimal(uzs),
            free_days=free_days,
        )

    return tariff


@pytest.fixture
def container_20ft(db):
    """Create a 20ft container."""
    return Container.objects.create(
        container_number="MSKU1234567",
        iso_type="22G1",  # 20ft standard
    )


@pytest.fixture
def container_40ft(db):
    """Create a 40ft container."""
    return Container.objects.create(
        container_number="TCLU9876543",
        iso_type="42G1",  # 40ft high cube
    )


@pytest.fixture
def container_entry_factory(db, admin_user):
    """Factory for creating container entries."""

    def _create(
        container,
        company=None,
        status="LADEN",
        entry_time=None,
        exit_date=None,
    ):
        if entry_time is None:
            entry_time = timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0))

        entry = ContainerEntry.objects.create(
            container=container,
            company=company,
            status=status,
            entry_time=entry_time,
            exit_date=exit_date,
            transport_type="TRUCK",
            transport_number="TEST001",
            recorded_by=admin_user,
        )
        return entry

    return _create


@pytest.fixture
def service():
    """Create StorageCostService instance."""
    return StorageCostService()


# ============================================================================
# Container Size Derivation Tests
# ============================================================================


class TestContainerSizeDerivation:
    """Tests for _derive_size_from_iso_type method."""

    def test_20ft_standard(self, service):
        """22G1 should be 20ft."""
        assert service._derive_size_from_iso_type("22G1") == ContainerSize.TWENTY_FT

    def test_20ft_reefer(self, service):
        """25R1 should be 20ft."""
        assert service._derive_size_from_iso_type("25R1") == ContainerSize.TWENTY_FT

    def test_20ft_tank(self, service):
        """20T1 should be 20ft."""
        assert service._derive_size_from_iso_type("20T1") == ContainerSize.TWENTY_FT

    def test_40ft_standard(self, service):
        """42G1 should be 40ft."""
        assert service._derive_size_from_iso_type("42G1") == ContainerSize.FORTY_FT

    def test_40ft_high_cube(self, service):
        """45G1 should be 40ft."""
        assert service._derive_size_from_iso_type("45G1") == ContainerSize.FORTY_FT

    def test_40ft_reefer(self, service):
        """45R1 should be 40ft."""
        assert service._derive_size_from_iso_type("45R1") == ContainerSize.FORTY_FT

    def test_45ft_treated_as_40ft(self, service):
        """L5G1 (45ft) should be treated as 40ft."""
        assert service._derive_size_from_iso_type("L5G1") == ContainerSize.FORTY_FT

    def test_none_defaults_to_20ft(self, service):
        """None ISO type should default to 20ft."""
        assert service._derive_size_from_iso_type(None) == ContainerSize.TWENTY_FT

    def test_empty_string_defaults_to_20ft(self, service):
        """Empty string should default to 20ft with warning."""
        # Empty string is treated like None - defaults to 20ft
        assert service._derive_size_from_iso_type("") == ContainerSize.TWENTY_FT

    def test_invalid_code_raises_error(self, service):
        """Invalid ISO code should raise InvalidContainerSizeError."""
        with pytest.raises(InvalidContainerSizeError):
            service._derive_size_from_iso_type("XYZ123")


# ============================================================================
# Status Mapping Tests
# ============================================================================


class TestStatusMapping:
    """Tests for _map_entry_status method."""

    def test_laden_status(self, service):
        """LADEN should map to laden."""
        assert service._map_entry_status("LADEN") == ContainerBillingStatus.LADEN

    def test_empty_status(self, service):
        """EMPTY should map to empty."""
        assert service._map_entry_status("EMPTY") == ContainerBillingStatus.EMPTY

    def test_unknown_defaults_to_laden(self, service):
        """Unknown status should default to laden."""
        assert service._map_entry_status("UNKNOWN") == ContainerBillingStatus.LADEN


# ============================================================================
# Single Period Calculation Tests
# ============================================================================


class TestSinglePeriodCalculation:
    """Tests for simple single-period cost calculations."""

    def test_simple_calculation_40ft_laden(
        self,
        service,
        general_tariff,
        container_40ft,
        container_entry_factory,
    ):
        """Test basic calculation for 40ft laden container."""
        # Entry: Jan 10, Exit: Jan 20 = 11 days
        # 5 free days + 6 billable days @ $18/day = $108
        entry = container_entry_factory(
            container=container_40ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 20, 10, 0, 0)),
        )

        result = service.calculate_cost(entry)

        assert result.container_size == ContainerSize.FORTY_FT
        assert result.container_status == ContainerBillingStatus.LADEN
        assert result.total_days == 11
        assert result.free_days_applied == 5
        assert result.billable_days == 6
        assert result.total_usd == Decimal("108.00")
        assert result.total_uzs == Decimal("1350000.00")
        assert len(result.periods) == 1

    def test_simple_calculation_20ft_empty(
        self,
        service,
        general_tariff,
        container_20ft,
        container_entry_factory,
    ):
        """Test basic calculation for 20ft empty container."""
        # Entry: Jan 10, Exit: Jan 15 = 6 days
        # 5 free days + 1 billable day @ $8/day = $8
        entry = container_entry_factory(
            container=container_20ft,
            status="EMPTY",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 15, 10, 0, 0)),
        )

        result = service.calculate_cost(entry)

        assert result.container_size == ContainerSize.TWENTY_FT
        assert result.container_status == ContainerBillingStatus.EMPTY
        assert result.total_days == 6
        assert result.free_days_applied == 5
        assert result.billable_days == 1
        assert result.total_usd == Decimal("8.00")

    def test_all_free_days(
        self,
        service,
        general_tariff,
        container_20ft,
        container_entry_factory,
    ):
        """Container within free period should have zero cost."""
        # Entry: Jan 10, Exit: Jan 12 = 3 days (within 5 free days)
        entry = container_entry_factory(
            container=container_20ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 12, 10, 0, 0)),
        )

        result = service.calculate_cost(entry)

        assert result.total_days == 3
        assert result.free_days_applied == 3
        assert result.billable_days == 0
        assert result.total_usd == Decimal("0.00")
        assert result.total_uzs == Decimal("0.00")

    def test_same_day_entry_exit(
        self,
        service,
        general_tariff,
        container_20ft,
        container_entry_factory,
    ):
        """Same day entry/exit should count as 1 day."""
        entry = container_entry_factory(
            container=container_20ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 10, 18, 0, 0)),
        )

        result = service.calculate_cost(entry)

        assert result.total_days == 1
        assert result.free_days_applied == 1
        assert result.billable_days == 0


# ============================================================================
# Special Tariff Tests
# ============================================================================


class TestSpecialTariff:
    """Tests for company-specific special tariffs."""

    def test_special_tariff_applied(
        self,
        service,
        general_tariff,
        special_tariff,
        test_company,
        container_40ft,
        container_entry_factory,
    ):
        """Company with special tariff should get discounted rate."""
        # Entry: Jan 10, Exit: Jan 25 = 16 days
        # Special tariff: 7 free days + 9 billable @ $14/day = $126
        entry = container_entry_factory(
            container=container_40ft,
            company=test_company,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 25, 10, 0, 0)),
        )

        result = service.calculate_cost(entry)

        assert result.total_days == 16
        assert result.free_days_applied == 7  # Special tariff has 7 free days
        assert result.billable_days == 9
        assert result.total_usd == Decimal("126.00")  # 9 * $14
        assert result.periods[0].tariff_type == "special"

    def test_general_tariff_without_company(
        self,
        service,
        general_tariff,
        special_tariff,
        container_40ft,
        container_entry_factory,
    ):
        """Container without company should use general tariff."""
        entry = container_entry_factory(
            container=container_40ft,
            company=None,  # No company
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 25, 10, 0, 0)),
        )

        result = service.calculate_cost(entry)

        assert result.free_days_applied == 5  # General tariff has 5 free days
        assert result.billable_days == 11
        assert result.total_usd == Decimal("198.00")  # 11 * $18
        assert result.periods[0].tariff_type == "general"


# ============================================================================
# Multi-Period Calculation Tests (Tariff Changes)
# ============================================================================


class TestMultiPeriodCalculation:
    """Tests for calculations spanning multiple tariff periods."""

    def test_tariff_change_mid_stay(
        self,
        db,
        admin_user,
        container_40ft,
        container_entry_factory,
    ):
        """Tariff changing mid-stay should split calculation by periods."""
        # Create old tariff (Jan 1 - Jan 14)
        old_tariff = Tariff.objects.create(
            company=None,
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 1, 14),
            created_by=admin_user,
        )
        TariffRate.objects.create(
            tariff=old_tariff,
            container_size=ContainerSize.FORTY_FT,
            container_status=ContainerBillingStatus.LADEN,
            daily_rate_usd=Decimal("10.00"),
            daily_rate_uzs=Decimal("125000.00"),
            free_days=3,
        )

        # Create new tariff (Jan 15+)
        new_tariff = Tariff.objects.create(
            company=None,
            effective_from=date(2025, 1, 15),
            effective_to=None,
            created_by=admin_user,
        )
        TariffRate.objects.create(
            tariff=new_tariff,
            container_size=ContainerSize.FORTY_FT,
            container_status=ContainerBillingStatus.LADEN,
            daily_rate_usd=Decimal("15.00"),
            daily_rate_uzs=Decimal("187500.00"),
            free_days=5,
        )

        # Entry: Jan 10, Exit: Jan 20
        # Period 1: Jan 10-14 (5 days) - 3 free + 2 billable @ $10 = $20
        # Period 2: Jan 15-20 (6 days) - 0 free + 6 billable @ $15 = $90
        # Total: $110
        entry = container_entry_factory(
            container=container_40ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 20, 10, 0, 0)),
        )

        service = StorageCostService()
        result = service.calculate_cost(entry)

        assert len(result.periods) == 2
        assert result.free_days_applied == 3  # Locked from first tariff
        assert result.total_usd == Decimal("110.00")

        # Check period breakdown
        assert result.periods[0].start_date == date(2025, 1, 10)
        assert result.periods[0].end_date == date(2025, 1, 14)
        assert result.periods[0].daily_rate_usd == Decimal("10.00")

        assert result.periods[1].start_date == date(2025, 1, 15)
        assert result.periods[1].end_date == date(2025, 1, 20)
        assert result.periods[1].daily_rate_usd == Decimal("15.00")


# ============================================================================
# Free Days Lock Tests
# ============================================================================


class TestFreeDaysLock:
    """Tests for free days locked at entry time."""

    def test_free_days_locked_at_entry(
        self,
        db,
        admin_user,
        container_40ft,
        container_entry_factory,
    ):
        """Free days should be locked when container enters."""
        # Old tariff with 10 free days (Jan 1-14)
        old_tariff = Tariff.objects.create(
            company=None,
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 1, 14),
            created_by=admin_user,
        )
        TariffRate.objects.create(
            tariff=old_tariff,
            container_size=ContainerSize.FORTY_FT,
            container_status=ContainerBillingStatus.LADEN,
            daily_rate_usd=Decimal("10.00"),
            daily_rate_uzs=Decimal("125000.00"),
            free_days=10,  # 10 free days
        )

        # New tariff with only 3 free days (Jan 15+)
        new_tariff = Tariff.objects.create(
            company=None,
            effective_from=date(2025, 1, 15),
            effective_to=None,
            created_by=admin_user,
        )
        TariffRate.objects.create(
            tariff=new_tariff,
            container_size=ContainerSize.FORTY_FT,
            container_status=ContainerBillingStatus.LADEN,
            daily_rate_usd=Decimal("15.00"),
            daily_rate_uzs=Decimal("187500.00"),
            free_days=3,  # Only 3 free days
        )

        # Entry: Jan 10 (under old tariff with 10 free days)
        # Exit: Jan 25 = 16 days total
        # Free days should be 10 (locked from entry), not 3
        entry = container_entry_factory(
            container=container_40ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 25, 10, 0, 0)),
        )

        service = StorageCostService()
        result = service.calculate_cost(entry)

        # Free days locked at 10 from entry date tariff
        assert result.free_days_applied == 10
        assert result.billable_days == 6  # 16 - 10


# ============================================================================
# Active Container Tests
# ============================================================================


class TestActiveContainerCalculation:
    """Tests for calculating costs of containers still in terminal."""

    def test_active_container_calculates_to_today(
        self,
        service,
        general_tariff,
        container_20ft,
        container_entry_factory,
    ):
        """Active container should calculate up to today."""
        # Entry yesterday, no exit date
        yesterday = timezone.now() - timedelta(days=1)
        entry = container_entry_factory(
            container=container_20ft,
            status="LADEN",
            entry_time=yesterday,
            exit_date=None,  # Still in terminal
        )

        result = service.calculate_cost(entry)

        assert result.is_active is True
        assert result.total_days >= 2  # At least 2 days

    def test_active_container_with_as_of_date(
        self,
        service,
        general_tariff,
        container_20ft,
        container_entry_factory,
    ):
        """as_of_date parameter should override calculation end date."""
        entry = container_entry_factory(
            container=container_20ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=None,
        )

        # Calculate up to Jan 20 only
        result = service.calculate_cost(entry, as_of_date=date(2025, 1, 20))

        assert result.end_date == date(2025, 1, 20)
        assert result.total_days == 11


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error conditions."""

    def test_no_tariff_raises_error(
        self,
        db,
        admin_user,
        container_20ft,
        container_entry_factory,
    ):
        """Missing tariff should raise TariffNotFoundError."""
        # Create entry without any tariffs in the system
        entry = container_entry_factory(
            container=container_20ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 15, 10, 0, 0)),
        )

        service = StorageCostService()

        with pytest.raises(TariffNotFoundError):
            service.calculate_cost(entry)


# ============================================================================
# Bulk Calculation Tests
# ============================================================================


class TestBulkCalculation:
    """Tests for bulk cost calculation."""

    def test_bulk_calculation(
        self,
        service,
        general_tariff,
        container_20ft,
        container_40ft,
        container_entry_factory,
    ):
        """Bulk calculation should return results for all containers."""
        entry1 = container_entry_factory(
            container=container_20ft,
            status="LADEN",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 10, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 20, 10, 0, 0)),
        )

        # Create another container
        container2 = Container.objects.create(
            container_number="ABCD1234567",
            iso_type="42G1",
        )
        entry2 = container_entry_factory(
            container=container2,
            status="EMPTY",
            entry_time=timezone.make_aware(timezone.datetime(2025, 1, 12, 10, 0, 0)),
            exit_date=timezone.make_aware(timezone.datetime(2025, 1, 22, 10, 0, 0)),
        )

        entries = ContainerEntry.objects.filter(id__in=[entry1.id, entry2.id])

        results = service.calculate_bulk_costs(entries)

        assert len(results) == 2
        assert all(r.total_usd >= Decimal("0") for r in results)
