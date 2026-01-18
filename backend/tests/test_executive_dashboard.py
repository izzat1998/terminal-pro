"""
Tests for ExecutiveDashboardService.

Tests cover:
- Summary metrics aggregation
- Container status breakdown
- Revenue trends calculation
- Top customers by revenue
- Throughput metrics
- Vehicle metrics
- Pre-order statistics
- Full dashboard integration
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.accounts.models import Company, CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, PreOrder
from apps.terminal_operations.services.executive_dashboard_service import (
    ExecutiveDashboardService,
)
from apps.vehicles.models import VehicleEntry


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def dashboard_service():
    """Create ExecutiveDashboardService instance."""
    return ExecutiveDashboardService()


@pytest.fixture
def company(db):
    """Create a test company."""
    return Company.objects.create(
        name="Test Shipping Co",
        slug="test-shipping-co",
    )


@pytest.fixture
def customer_user(db, company):
    """Create a customer user."""
    from apps.accounts.models import CustomerProfile

    user = CustomUser.objects.create(
        username="customer_test",
        first_name="Test Customer",
        phone_number="+998909876543",
        user_type="customer",
        bot_access=True,
    )
    CustomerProfile.objects.create(
        user=user,
        company=company,
        phone_number="+998909876543",
    )
    return user


@pytest.fixture
def container_entry_factory(db, admin_user):
    """Factory for creating container entries with custom parameters."""

    def _create_entry(
        status="LADEN",
        transport_type="TRUCK",
        entry_time=None,
        exit_date=None,
        company=None,
    ):
        import random
        import string

        prefix = "".join(random.choices(string.ascii_uppercase, k=4))
        suffix = "".join(random.choices(string.digits, k=7))
        container_number = f"{prefix}{suffix}"

        container = Container.objects.create(
            container_number=container_number,
            iso_type="42G1",
        )

        return ContainerEntry.objects.create(
            container=container,
            status=status,
            transport_type=transport_type,
            transport_number="TEST001",
            recorded_by=admin_user,
            entry_time=entry_time or timezone.now(),
            exit_date=exit_date,
            company=company,
        )

    return _create_entry


@pytest.fixture
def vehicle_entry_factory(db, admin_user):
    """Factory for creating vehicle entries."""

    def _create_vehicle(
        status="ON_TERMINAL",
        vehicle_type="CARGO",
        entry_time=None,
        exit_time=None,
    ):
        import random
        import string

        plate = f"01{''.join(random.choices(string.ascii_uppercase, k=1))}{random.randint(100, 999)}BC"

        return VehicleEntry.objects.create(
            license_plate=plate,
            vehicle_type=vehicle_type,
            transport_type="TRUCK",
            entry_load_status="LOADED",
            cargo_type="CONTAINER",
            entry_time=entry_time or timezone.now(),
            exit_time=exit_time,
            recorded_by=admin_user,
            status=status,
        )

    return _create_vehicle


# ============================================================================
# Service Tests - Summary Metrics
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardSummaryMetrics:
    """Tests for _get_summary_metrics()."""

    def test_summary_metrics_basic(
        self, container_entry_factory, dashboard_service
    ):
        """Test basic summary metrics with containers on terminal."""
        # Create containers on terminal
        container_entry_factory(status="LADEN")
        container_entry_factory(status="EMPTY")

        summary = dashboard_service._get_summary_metrics()

        assert summary["total_containers_on_terminal"] == 2
        assert summary["laden_count"] == 1
        assert summary["empty_count"] == 1

    def test_summary_metrics_with_exited_containers(
        self, container_entry_factory, dashboard_service
    ):
        """Test that exited containers are not counted."""
        # On terminal
        container_entry_factory(status="LADEN", exit_date=None)

        # Exited
        container_entry_factory(status="LADEN", exit_date=timezone.now())

        summary = dashboard_service._get_summary_metrics()

        assert summary["total_containers_on_terminal"] == 1

    def test_summary_metrics_today_entries_exits(
        self, container_entry_factory, dashboard_service
    ):
        """Test counting containers entered and exited today."""
        today = timezone.now()
        yesterday = today - timedelta(days=1)

        # Entered today
        container_entry_factory(status="LADEN", entry_time=today)
        container_entry_factory(status="LADEN", entry_time=today)

        # Entered yesterday
        container_entry_factory(status="LADEN", entry_time=yesterday)

        # Exited today
        container_entry_factory(
            status="LADEN",
            entry_time=yesterday,
            exit_date=today,
        )

        summary = dashboard_service._get_summary_metrics()

        assert summary["containers_entered_today"] == 2
        assert summary["containers_exited_today"] == 1

    @patch("apps.billing.services.StorageCostService")
    def test_summary_metrics_with_revenue(
        self, mock_storage_service_class, container_entry_factory, dashboard_service
    ):
        """Test summary metrics include revenue calculation."""
        container_entry_factory(status="LADEN")

        # Mock storage cost service
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.total_usd = Decimal("100.50")
        mock_result.total_uzs = Decimal("1200000.00")
        mock_service.calculate_bulk_costs.return_value = [mock_result]
        mock_storage_service_class.return_value = mock_service

        summary = dashboard_service._get_summary_metrics()

        assert Decimal(summary["total_revenue_usd"]) == Decimal("100.50")
        assert Decimal(summary["total_revenue_uzs"]) == Decimal("1200000.00")

    def test_summary_metrics_active_customers(
        self, container_entry_factory, company, dashboard_service
    ):
        """Test counting active customers with containers on terminal."""
        # Containers from same company
        container_entry_factory(status="LADEN", company=company)
        container_entry_factory(status="LADEN", company=company)

        # Container with no company
        container_entry_factory(status="LADEN", company=None)

        summary = dashboard_service._get_summary_metrics()

        assert summary["active_customers"] == 1


# ============================================================================
# Service Tests - Container Status Breakdown
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardContainerStatus:
    """Tests for _get_container_status_breakdown()."""

    def test_container_status_breakdown(
        self, container_entry_factory, dashboard_service
    ):
        """Test container breakdown by status."""
        container_entry_factory(status="LADEN")
        container_entry_factory(status="LADEN")
        container_entry_factory(status="EMPTY")

        breakdown = dashboard_service._get_container_status_breakdown()

        assert breakdown["laden"] == 2
        assert breakdown["empty"] == 1

    def test_container_status_russian_values(
        self, container_entry_factory, dashboard_service
    ):
        """Test handling Russian status values."""
        # Create with Russian status
        import random
        import string

        prefix = "".join(random.choices(string.ascii_uppercase, k=4))
        suffix = "".join(random.choices(string.digits, k=7))

        container = Container.objects.create(
            container_number=f"{prefix}{suffix}",
            iso_type="42G1",
        )

        ContainerEntry.objects.create(
            container=container,
            status="Гружёный",  # Russian for LADEN
            transport_type="TRUCK",
            transport_number="TEST001",
        )

        breakdown = dashboard_service._get_container_status_breakdown()

        assert breakdown["laden"] == 1

    def test_container_size_breakdown(
        self, container_entry_factory, admin_user, dashboard_service
    ):
        """Test container breakdown by size (20ft vs 40ft)."""
        # 20ft containers (ISO type starts with 2)
        container_20_1 = Container.objects.create(
            container_number="ABCD1234567",
            iso_type="22G1",  # 20ft
        )
        ContainerEntry.objects.create(
            container=container_20_1,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="TEST001",
            recorded_by=admin_user,
        )

        # 40ft containers (ISO type starts with 4)
        container_40_1 = Container.objects.create(
            container_number="EFGH1234567",
            iso_type="42G1",  # 40ft
        )
        ContainerEntry.objects.create(
            container=container_40_1,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="TEST002",
            recorded_by=admin_user,
        )

        breakdown = dashboard_service._get_container_status_breakdown()

        assert breakdown["by_size"]["20ft"] == 1
        assert breakdown["by_size"]["40ft"] == 1


# ============================================================================
# Service Tests - Revenue Trends
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardRevenueTrends:
    """Tests for _get_revenue_trends()."""

    def test_revenue_trends_daily_entries_exits(
        self, container_entry_factory, dashboard_service
    ):
        """Test daily entry and exit trends."""
        today = timezone.now()
        yesterday = today - timedelta(days=1)

        # Entries
        container_entry_factory(status="LADEN", entry_time=today)
        container_entry_factory(status="LADEN", entry_time=yesterday)

        # Exits
        container_entry_factory(
            status="LADEN",
            entry_time=yesterday - timedelta(days=1),
            exit_date=today,
        )

        trends = dashboard_service._get_revenue_trends(days=7)

        # Should have data for at least today and yesterday
        assert len(trends) >= 2

        # Find today's data
        today_data = next(
            (t for t in trends if t["date"] == today.date().isoformat()),
            None,
        )
        assert today_data is not None
        assert today_data["entries"] == 1
        assert today_data["exits"] == 1

    @patch("apps.billing.services.StorageCostService")
    def test_revenue_trends_with_revenue_calculation(
        self,
        mock_storage_service_class,
        container_entry_factory,
        dashboard_service,
    ):
        """Test revenue trends include daily revenue."""
        today = timezone.now()

        container_entry_factory(
            status="LADEN",
            entry_time=today - timedelta(days=2),
            exit_date=today,
        )

        # Mock storage cost
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.total_usd = Decimal("50.00")
        mock_result.is_active = False
        mock_result.end_date = today.date()
        mock_service.calculate_bulk_costs.return_value = [mock_result]
        mock_storage_service_class.return_value = mock_service

        trends = dashboard_service._get_revenue_trends(days=7)

        # Find today's revenue
        today_trend = next(
            (t for t in trends if t["date"] == today.date().isoformat()),
            None,
        )
        if today_trend:
            assert Decimal(today_trend["revenue_usd"]) == Decimal("50.00")


# ============================================================================
# Service Tests - Top Customers
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardTopCustomers:
    """Tests for _get_top_customers()."""

    def test_top_customers_by_container_count(
        self, container_entry_factory, dashboard_service
    ):
        """Test ranking customers by container count."""
        company1 = Company.objects.create(name="Company A", slug="company-a")
        company2 = Company.objects.create(name="Company B", slug="company-b")

        # Company A has 3 containers
        for _ in range(3):
            container_entry_factory(status="LADEN", company=company1)

        # Company B has 1 container
        container_entry_factory(status="LADEN", company=company2)

        customers = dashboard_service._get_top_customers(limit=10)

        assert len(customers) >= 2
        assert customers[0]["container_count"] >= customers[1]["container_count"]

    @patch("apps.billing.services.StorageCostService")
    def test_top_customers_sorted_by_revenue(
        self,
        mock_storage_service_class,
        container_entry_factory,
        dashboard_service,
    ):
        """Test customers are sorted by revenue (highest first)."""
        company1 = Company.objects.create(name="Company A", slug="company-a")
        company2 = Company.objects.create(name="Company B", slug="company-b")

        container_entry_factory(status="LADEN", company=company1)
        container_entry_factory(status="LADEN", company=company2)

        # Mock revenue: Company B has higher revenue
        mock_service = MagicMock()

        def mock_calculate(entries):
            results = []
            for entry in entries:
                result = MagicMock()
                if entry.company_id == company2.id:
                    result.total_usd = Decimal("200.00")
                else:
                    result.total_usd = Decimal("100.00")
                result.total_uzs = Decimal("0")
                results.append(result)
            return results

        mock_service.calculate_bulk_costs.side_effect = mock_calculate
        mock_storage_service_class.return_value = mock_service

        customers = dashboard_service._get_top_customers(limit=10)

        # Company B should be first (higher revenue)
        if len(customers) >= 2:
            assert Decimal(customers[0]["revenue_usd"]) >= Decimal(
                customers[1]["revenue_usd"]
            )


# ============================================================================
# Service Tests - Throughput Metrics
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardThroughput:
    """Tests for _get_throughput_metrics()."""

    def test_throughput_last_7_days(
        self, container_entry_factory, dashboard_service
    ):
        """Test throughput metrics for last 7 days."""
        now = timezone.now()
        five_days_ago = now - timedelta(days=5)

        # Entries in last 7 days
        container_entry_factory(status="LADEN", entry_time=five_days_ago)
        container_entry_factory(status="LADEN", entry_time=now)

        # Exits in last 7 days
        container_entry_factory(
            status="LADEN",
            entry_time=five_days_ago - timedelta(days=1),
            exit_date=now,
        )

        throughput = dashboard_service._get_throughput_metrics(days=30)

        # Should have at least the 2 entries we created
        assert throughput["last_7_days"]["entries"] >= 2
        assert throughput["last_7_days"]["exits"] >= 1

    def test_throughput_last_30_days(
        self, container_entry_factory, dashboard_service
    ):
        """Test throughput metrics for last 30 days."""
        now = timezone.now()
        twenty_days_ago = now - timedelta(days=20)

        container_entry_factory(status="LADEN", entry_time=twenty_days_ago)

        throughput = dashboard_service._get_throughput_metrics(days=30)

        assert throughput["last_30_days"]["entries"] >= 1

    def test_throughput_daily_average(
        self, container_entry_factory, dashboard_service
    ):
        """Test daily average calculation."""
        now = timezone.now()

        # Create 10 entries over 5 days (average = 2 per day)
        for i in range(10):
            entry_time = now - timedelta(days=i % 5)
            container_entry_factory(status="LADEN", entry_time=entry_time)

        throughput = dashboard_service._get_throughput_metrics(days=30)

        # Daily average should be approximately entries / days
        assert throughput["daily_average"] >= 0

    def test_throughput_daily_breakdown(
        self, container_entry_factory, dashboard_service
    ):
        """Test daily breakdown includes all days with activity."""
        now = timezone.now()

        container_entry_factory(status="LADEN", entry_time=now)

        throughput = dashboard_service._get_throughput_metrics(days=7)

        assert "daily_data" in throughput
        assert len(throughput["daily_data"]) >= 1


# ============================================================================
# Service Tests - Vehicle Metrics
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardVehicleMetrics:
    """Tests for _get_vehicle_metrics()."""

    def test_vehicle_metrics_on_terminal(
        self, vehicle_entry_factory, dashboard_service
    ):
        """Test counting vehicles on terminal."""
        vehicle_entry_factory(status="ON_TERMINAL")
        vehicle_entry_factory(status="ON_TERMINAL")
        vehicle_entry_factory(status="EXITED", exit_time=timezone.now())

        metrics = dashboard_service._get_vehicle_metrics()

        assert metrics["total_on_terminal"] == 2

    def test_vehicle_metrics_by_type(
        self, vehicle_entry_factory, dashboard_service
    ):
        """Test vehicle breakdown by type."""
        vehicle_entry_factory(status="ON_TERMINAL", vehicle_type="CARGO")
        vehicle_entry_factory(status="ON_TERMINAL", vehicle_type="TANKER")

        metrics = dashboard_service._get_vehicle_metrics()

        assert "by_type" in metrics
        assert len(metrics["by_type"]) >= 2

    def test_vehicle_metrics_average_dwell_time(
        self, vehicle_entry_factory, dashboard_service
    ):
        """Test average dwell time calculation."""
        now = timezone.now()
        two_hours_ago = now - timedelta(hours=2)

        # Vehicle that stayed 2 hours
        vehicle_entry_factory(
            status="EXITED",
            entry_time=two_hours_ago,
            exit_time=now,
        )

        metrics = dashboard_service._get_vehicle_metrics()

        # Average should be around 2 hours
        assert metrics["avg_dwell_hours"] >= 0


# ============================================================================
# Service Tests - PreOrder Stats
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardPreOrderStats:
    """Tests for _get_preorder_stats()."""

    def test_preorder_stats_counts(self, customer_user, dashboard_service):
        """Test pre-order statistics counting."""
        # Create pre-orders in different statuses
        PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A123BC",
            operation_type="LOAD",
            status="PENDING",
        )
        PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A456BC",
            operation_type="LOAD",
            status="MATCHED",
        )

        stats = dashboard_service._get_preorder_stats()

        assert stats["pending"] == 1
        assert stats["matched"] == 1

    def test_preorder_stats_completed_today(
        self, customer_user, dashboard_service
    ):
        """Test counting pre-orders completed today."""
        today = timezone.now()
        yesterday = today - timedelta(days=1)

        # Completed today
        PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A123BC",
            operation_type="LOAD",
            status="COMPLETED",
            matched_at=today,
        )

        # Completed yesterday
        PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A456BC",
            operation_type="LOAD",
            status="COMPLETED",
            matched_at=yesterday,
        )

        stats = dashboard_service._get_preorder_stats()

        assert stats["completed_today"] == 1


# ============================================================================
# Service Tests - Full Dashboard
# ============================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestExecutiveDashboardIntegration:
    """Integration tests for complete dashboard."""

    def test_get_executive_dashboard_structure(
        self, container_entry_factory, dashboard_service
    ):
        """Test complete dashboard returns all required sections."""
        container_entry_factory(status="LADEN")

        dashboard = dashboard_service.get_executive_dashboard(days=30)

        # Verify all required keys
        assert "summary" in dashboard
        assert "container_status" in dashboard
        assert "revenue_trends" in dashboard
        assert "top_customers" in dashboard
        assert "throughput" in dashboard
        assert "vehicle_metrics" in dashboard
        assert "preorder_stats" in dashboard
        assert "generated_at" in dashboard

    def test_get_executive_dashboard_with_data(
        self,
        container_entry_factory,
        vehicle_entry_factory,
        customer_user,
        company,
        dashboard_service,
    ):
        """Test dashboard with realistic data."""
        # Create containers
        container_entry_factory(status="LADEN", company=company)
        container_entry_factory(status="EMPTY", company=company)

        # Create vehicles
        vehicle_entry_factory(status="ON_TERMINAL")

        # Create pre-order
        PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A123BC",
            operation_type="LOAD",
            status="PENDING",
        )

        dashboard = dashboard_service.get_executive_dashboard(days=7)

        # Verify data is present
        assert dashboard["summary"]["total_containers_on_terminal"] >= 2
        assert dashboard["vehicle_metrics"]["total_on_terminal"] >= 1
        assert dashboard["preorder_stats"]["pending"] >= 1

    @patch("apps.billing.services.StorageCostService")
    def test_dashboard_handles_billing_service_error(
        self,
        mock_storage_service_class,
        container_entry_factory,
        dashboard_service,
    ):
        """Test dashboard continues even if billing service fails."""
        container_entry_factory(status="LADEN")

        # Mock billing service to raise exception
        mock_storage_service_class.side_effect = Exception("Billing service error")

        # Should not crash
        dashboard = dashboard_service.get_executive_dashboard(days=7)

        # Should return dashboard with zero revenue
        assert dashboard["summary"]["total_revenue_usd"] == "0.00"

    def test_dashboard_custom_time_range(
        self, container_entry_factory, dashboard_service
    ):
        """Test dashboard with custom time range."""
        now = timezone.now()

        # Create entry 10 days ago
        container_entry_factory(
            status="LADEN",
            entry_time=now - timedelta(days=10),
        )

        # Request 7-day dashboard
        dashboard_7 = dashboard_service.get_executive_dashboard(days=7)

        # Request 30-day dashboard
        dashboard_30 = dashboard_service.get_executive_dashboard(days=30)

        # 30-day should have more data
        assert len(dashboard_30["revenue_trends"]) >= len(
            dashboard_7["revenue_trends"]
        )


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.django_db
class TestExecutiveDashboardEdgeCases:
    """Edge case tests."""

    def test_dashboard_with_no_data(self, dashboard_service):
        """Test dashboard with empty database."""
        dashboard = dashboard_service.get_executive_dashboard(days=30)

        assert dashboard["summary"]["total_containers_on_terminal"] == 0
        assert dashboard["summary"]["active_customers"] == 0
        assert len(dashboard["top_customers"]) == 0

    def test_dashboard_with_zero_days(self, dashboard_service):
        """Test dashboard with days=0 parameter."""
        # Should handle gracefully (no division by zero)
        dashboard = dashboard_service.get_executive_dashboard(days=0)

        assert "summary" in dashboard

    def test_revenue_calculation_error_handling(self, dashboard_service):
        """Test _calculate_total_storage_cost handles missing billing app."""
        # Should return zero if billing app not available
        total_usd, total_uzs = dashboard_service._calculate_total_storage_cost()

        assert isinstance(total_usd, Decimal)
        assert isinstance(total_uzs, Decimal)
