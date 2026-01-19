"""
Tests for the Monthly Statement Service.

Tests cover:
- Statement generation for split billing
- Statement generation for exit-month billing
- Returning existing statements (caching behavior)
- Regeneration of statements
- Available periods retrieval
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import Company, CustomUser
from apps.billing.models import MonthlyStatement, Tariff, TariffRate
from apps.billing.services.statement_service import MonthlyStatementService
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry


# ============================================================================
# Fixtures
# ============================================================================


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


# ============================================================================
# Statement Generation Tests
# ============================================================================


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


# ============================================================================
# Split Billing Tests
# ============================================================================


@pytest.mark.django_db
class TestSplitBillingMethod:
    def test_split_billing_includes_partial_month(
        self, company, admin_user, general_tariff
    ):
        """Split billing should include containers active during any part of the month."""
        # Create container that spans months
        container = Container.objects.create(
            container_number="SPLT1234567",
            iso_type="42G1",
        )
        ContainerEntry.objects.create(
            container=container,
            company=company,
            entry_time=timezone.make_aware(datetime(2025, 12, 20, 10, 0, 0)),
            exit_date=timezone.make_aware(datetime(2026, 1, 15, 10, 0, 0)),
            status="LADEN",
            transport_type="TRUCK",
            transport_number="TEST001",
            recorded_by=admin_user,
        )

        service = MonthlyStatementService()
        statement = service.get_or_generate_statement(
            company=company,
            year=2026,
            month=1,
            user=admin_user,
        )

        # Container should be included in January even though it started in December
        assert statement.total_containers >= 1


# ============================================================================
# Exit Month Billing Tests
# ============================================================================


@pytest.mark.django_db
class TestExitMonthBillingMethod:
    def test_exit_month_includes_only_exited(self, db, admin_user, general_tariff):
        """Exit-month billing should only include containers that exited in that month."""
        # Create company with exit_month billing
        exit_company = Company.objects.create(
            name="Exit Month Company",
            billing_method="exit_month",
        )

        # Create container that exited in January
        container = Container.objects.create(
            container_number="EXTI1234567",
            iso_type="42G1",
        )
        ContainerEntry.objects.create(
            container=container,
            company=exit_company,
            entry_time=timezone.make_aware(datetime(2025, 12, 1, 10, 0, 0)),
            exit_date=timezone.make_aware(datetime(2026, 1, 10, 10, 0, 0)),
            status="LADEN",
            transport_type="TRUCK",
            transport_number="TEST001",
            recorded_by=admin_user,
        )

        service = MonthlyStatementService()
        statement = service.get_or_generate_statement(
            company=exit_company,
            year=2026,
            month=1,
            user=admin_user,
        )

        # Container should be included because it exited in January
        assert statement.total_containers >= 1

    def test_exit_month_excludes_active_containers(self, db, admin_user, general_tariff):
        """Exit-month billing should exclude containers still on terminal."""
        exit_company = Company.objects.create(
            name="Exit Month Company 2",
            billing_method="exit_month",
        )

        # Create container still on terminal
        container = Container.objects.create(
            container_number="ACTI1234567",
            iso_type="42G1",
        )
        ContainerEntry.objects.create(
            container=container,
            company=exit_company,
            entry_time=timezone.make_aware(datetime(2026, 1, 5, 10, 0, 0)),
            exit_date=None,  # Still on terminal
            status="LADEN",
            transport_type="TRUCK",
            transport_number="TEST001",
            recorded_by=admin_user,
        )

        service = MonthlyStatementService()
        statement = service.get_or_generate_statement(
            company=exit_company,
            year=2026,
            month=1,
            user=admin_user,
        )

        # Active container should NOT be included in exit-month billing
        assert statement.total_containers == 0


# ============================================================================
# Available Periods Tests
# ============================================================================


@pytest.mark.django_db
class TestAvailablePeriods:
    def test_marks_existing_statements(self, company, container_entry, general_tariff, admin_user):
        """Available periods should mark months that have generated statements."""
        service = MonthlyStatementService()

        # First check - no statements yet
        periods_before = service.get_available_periods(company)
        jan_before = next(p for p in periods_before if p["year"] == 2026 and p["month"] == 1)
        assert jan_before["has_statement"] is False

        # Generate a statement
        service.get_or_generate_statement(company, 2026, 1, user=admin_user)

        # Check again - should now be marked
        periods_after = service.get_available_periods(company)
        jan_after = next(p for p in periods_after if p["year"] == 2026 and p["month"] == 1)
        assert jan_after["has_statement"] is True

    def test_returns_correct_labels(self, company, container_entry, general_tariff):
        """Available periods should have Russian month labels."""
        service = MonthlyStatementService()
        periods = service.get_available_periods(company)

        jan_period = next(p for p in periods if p["year"] == 2026 and p["month"] == 1)
        assert "Январь" in jan_period["label"]
        assert "2026" in jan_period["label"]
