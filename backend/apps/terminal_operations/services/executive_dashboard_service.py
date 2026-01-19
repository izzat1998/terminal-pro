"""
Executive Dashboard Service

Aggregates all terminal metrics for CEO/executive dashboard in a single optimized call.
Combines container, vehicle, revenue, and customer analytics into one response.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.core.services import BaseService
from apps.vehicles.models import VehicleEntry

from ..models import ContainerEntry, PreOrder


# Status filters supporting both Russian and English values
LADEN_FILTER = Q(status="LADEN") | Q(status="Гружёный")
EMPTY_FILTER = Q(status="EMPTY") | Q(status="Порожний")


class ExecutiveDashboardService(BaseService):
    """
    Service for aggregating executive dashboard metrics.

    Provides comprehensive terminal KPIs including:
    - Summary metrics (containers, revenue, vehicles)
    - Container status breakdown
    - Revenue trends (30-day)
    - Top customers by revenue and container count
    - Throughput metrics (entries/exits)
    - Vehicle metrics
    - Pre-order statistics
    """

    def get_executive_dashboard(self, days: int = 30) -> dict:
        """
        Get all executive dashboard metrics in a single call.

        Args:
            days: Number of days for historical trends (default 30)

        Returns:
            Complete dashboard data structure
        """
        now = timezone.now()

        # Collect all metrics
        summary = self._get_summary_metrics()
        container_status = self._get_container_status_breakdown()
        revenue_trends = self._get_revenue_trends(days)
        top_customers = self._get_top_customers(limit=10)
        throughput = self._get_throughput_metrics(days)
        vehicle_metrics = self._get_vehicle_metrics()
        preorder_stats = self._get_preorder_stats()

        self.logger.info("Generated executive dashboard metrics")

        return {
            "summary": summary,
            "container_status": container_status,
            "revenue_trends": revenue_trends,
            "top_customers": top_customers,
            "throughput": throughput,
            "vehicle_metrics": vehicle_metrics,
            "preorder_stats": preorder_stats,
            "generated_at": now.isoformat(),
        }

    def _get_summary_metrics(self) -> dict:
        """Get high-level summary KPIs."""
        today = timezone.now().date()

        container_stats = ContainerEntry.objects.aggregate(
            total_on_terminal=Count("id", filter=Q(exit_date__isnull=True)),
            laden=Count("id", filter=Q(exit_date__isnull=True) & LADEN_FILTER),
            empty=Count("id", filter=Q(exit_date__isnull=True) & EMPTY_FILTER),
            entered_today=Count("id", filter=Q(entry_time__date=today)),
            exited_today=Count("id", filter=Q(exit_date__date=today)),
        )

        # Vehicle count
        vehicles_on_terminal = VehicleEntry.objects.filter(status="ON_TERMINAL").count()

        # Active customers (companies with containers on terminal)
        active_customers = (
            ContainerEntry.objects.filter(exit_date__isnull=True, company__isnull=False)
            .values("company")
            .distinct()
            .count()
        )

        # Calculate total storage cost
        total_usd, total_uzs = self._calculate_total_storage_cost()

        return {
            "total_containers_on_terminal": container_stats["total_on_terminal"],
            "total_revenue_usd": str(total_usd),
            "total_revenue_uzs": str(total_uzs),
            "containers_entered_today": container_stats["entered_today"],
            "containers_exited_today": container_stats["exited_today"],
            "vehicles_on_terminal": vehicles_on_terminal,
            "active_customers": active_customers,
            "laden_count": container_stats["laden"],
            "empty_count": container_stats["empty"],
        }

    def _calculate_total_storage_cost(self) -> tuple[Decimal, Decimal]:
        """Calculate total storage cost for all containers on terminal."""
        total_usd = Decimal("0.00")
        total_uzs = Decimal("0.00")

        try:
            from apps.billing.services import StorageCostService

            on_terminal_entries = ContainerEntry.objects.filter(
                exit_date__isnull=True
            ).select_related("container", "company")

            if on_terminal_entries.exists():
                storage_service = StorageCostService()
                cost_results = storage_service.calculate_bulk_costs(on_terminal_entries)
                for result in cost_results:
                    total_usd += result.total_usd
                    total_uzs += result.total_uzs
        except Exception as e:
            self.logger.warning(f"Failed to calculate storage costs: {e}")

        return total_usd, total_uzs

    def _get_container_status_breakdown(self) -> dict:
        """Get container breakdown by status and size."""
        on_terminal = ContainerEntry.objects.filter(exit_date__isnull=True)

        laden = on_terminal.filter(LADEN_FILTER).count()
        empty = on_terminal.filter(EMPTY_FILTER).count()

        # Size breakdown based on ISO type first character
        # ISO type starts with size indicator: 2=20ft, 4=40ft, 5=45ft (treated as 40ft)
        size_20ft = on_terminal.filter(container__iso_type__regex=r"^2").count()
        size_40ft = on_terminal.filter(container__iso_type__regex=r"^[45]").count()

        return {
            "laden": laden,
            "empty": empty,
            "by_size": {
                "20ft": size_20ft,
                "40ft": size_40ft,
            },
        }

    def _get_revenue_trends(self, days: int = 30) -> list[dict]:
        """
        Get daily revenue and entry/exit trends.

        Calculates approximate daily revenue based on containers that exited
        and their billable days during that period.
        """
        now = timezone.now()
        start_date = now - timedelta(days=days)

        # Get daily entries and exits
        daily_entries = (
            ContainerEntry.objects.filter(entry_time__gte=start_date)
            .annotate(date=TruncDate("entry_time"))
            .values("date")
            .annotate(entries=Count("id"))
            .order_by("date")
        )

        daily_exits = (
            ContainerEntry.objects.filter(
                exit_date__isnull=False, exit_date__gte=start_date
            )
            .annotate(date=TruncDate("exit_date"))
            .values("date")
            .annotate(exits=Count("id"))
            .order_by("date")
        )

        # Merge entries and exits by date
        entries_dict = {item["date"]: item["entries"] for item in daily_entries}
        exits_dict = {item["date"]: item["exits"] for item in daily_exits}

        # Get all dates in range
        all_dates = set(entries_dict.keys()) | set(exits_dict.keys())

        # Calculate revenue for exited containers
        revenue_by_date = self._calculate_revenue_by_exit_date(start_date)

        trends = []
        for date in sorted(all_dates):
            trends.append(
                {
                    "date": date.isoformat(),
                    "entries": entries_dict.get(date, 0),
                    "exits": exits_dict.get(date, 0),
                    "revenue_usd": str(revenue_by_date.get(date, Decimal("0.00"))),
                }
            )

        return trends

    def _calculate_revenue_by_exit_date(self, start_date) -> dict:
        """Calculate revenue grouped by exit date."""
        revenue_by_date = {}

        try:
            from apps.billing.services import StorageCostService

            exited_entries = ContainerEntry.objects.filter(
                exit_date__isnull=False, exit_date__gte=start_date
            ).select_related("container", "company")

            if exited_entries.exists():
                storage_service = StorageCostService()
                cost_results = storage_service.calculate_bulk_costs(exited_entries)

                for result in cost_results:
                    # For exited containers, end_date is the exit date
                    # is_active=False means container has exited
                    if not result.is_active and result.end_date:
                        exit_date = result.end_date
                        if exit_date not in revenue_by_date:
                            revenue_by_date[exit_date] = Decimal("0.00")
                        revenue_by_date[exit_date] += result.total_usd

        except Exception as e:
            self.logger.warning(f"Failed to calculate revenue by date: {e}")

        return revenue_by_date

    def _get_top_customers(self, limit: int = 10) -> list[dict]:
        """Get top customers by container count and revenue."""
        # Get companies with most containers on terminal
        company_stats = (
            ContainerEntry.objects.filter(exit_date__isnull=True, company__isnull=False)
            .values("company__id", "company__name", "company__slug")
            .annotate(container_count=Count("id"))
            .order_by("-container_count")[:limit]
        )

        # Calculate revenue per company
        customers = []
        for stat in company_stats:
            company_id = stat["company__id"]
            company_revenue = self._calculate_company_revenue(company_id)

            customers.append(
                {
                    "company_id": company_id,
                    "company_name": stat["company__name"],
                    "company_slug": stat["company__slug"],
                    "container_count": stat["container_count"],
                    "revenue_usd": str(company_revenue),
                }
            )

        # Sort by revenue (highest first)
        customers.sort(key=lambda x: Decimal(x["revenue_usd"]), reverse=True)

        return customers

    def _calculate_company_revenue(self, company_id: int) -> Decimal:
        """Calculate total storage revenue for a company's containers on terminal."""
        total_usd = Decimal("0.00")

        try:
            from apps.billing.services import StorageCostService

            company_entries = ContainerEntry.objects.filter(
                exit_date__isnull=True, company_id=company_id
            ).select_related("container", "company")

            if company_entries.exists():
                storage_service = StorageCostService()
                cost_results = storage_service.calculate_bulk_costs(company_entries)
                for result in cost_results:
                    total_usd += result.total_usd

        except Exception as e:
            self.logger.warning(
                f"Failed to calculate revenue for company {company_id}: {e}"
            )

        return total_usd

    def _get_throughput_metrics(self, days: int = 30) -> dict:
        """Get container entry/exit throughput metrics."""
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=days)

        # Last 7 days
        entries_7d = ContainerEntry.objects.filter(
            entry_time__gte=seven_days_ago
        ).count()
        exits_7d = ContainerEntry.objects.filter(
            exit_date__isnull=False, exit_date__gte=seven_days_ago
        ).count()

        # Last 30 days
        entries_30d = ContainerEntry.objects.filter(
            entry_time__gte=thirty_days_ago
        ).count()
        exits_30d = ContainerEntry.objects.filter(
            exit_date__isnull=False, exit_date__gte=thirty_days_ago
        ).count()

        # Daily average (based on 30 days)
        daily_average = round(entries_30d / days, 1) if days > 0 else 0

        # Daily breakdown for chart
        daily_data = (
            ContainerEntry.objects.filter(entry_time__gte=thirty_days_ago)
            .annotate(date=TruncDate("entry_time"))
            .values("date")
            .annotate(entries=Count("id"))
            .order_by("date")
        )

        daily_exits = (
            ContainerEntry.objects.filter(
                exit_date__isnull=False, exit_date__gte=thirty_days_ago
            )
            .annotate(date=TruncDate("exit_date"))
            .values("date")
            .annotate(exits=Count("id"))
            .order_by("date")
        )

        # Merge into daily data
        entries_dict = {item["date"]: item["entries"] for item in daily_data}
        exits_dict = {item["date"]: item["exits"] for item in daily_exits}
        all_dates = sorted(set(entries_dict.keys()) | set(exits_dict.keys()))

        daily_breakdown = [
            {
                "date": date.isoformat(),
                "entries": entries_dict.get(date, 0),
                "exits": exits_dict.get(date, 0),
            }
            for date in all_dates
        ]

        return {
            "last_7_days": {"entries": entries_7d, "exits": exits_7d},
            "last_30_days": {"entries": entries_30d, "exits": exits_30d},
            "daily_average": daily_average,
            "daily_data": daily_breakdown,
        }

    def _get_vehicle_metrics(self) -> dict:
        """Get vehicle statistics for dashboard."""
        now = timezone.now()

        # Vehicles on terminal
        on_terminal = VehicleEntry.objects.filter(status="ON_TERMINAL")
        total_on_terminal = on_terminal.count()

        # By type
        by_type = {}
        type_counts = on_terminal.values("vehicle_type").annotate(count=Count("id"))
        for item in type_counts:
            vtype = item["vehicle_type"]
            label = dict(VehicleEntry.VEHICLE_TYPE_CHOICES).get(vtype, vtype)
            by_type[vtype] = {"count": item["count"], "label": label}

        # Average dwell time (last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        exited_vehicles = VehicleEntry.objects.filter(
            exit_time__isnull=False,
            entry_time__isnull=False,
            exit_time__gte=thirty_days_ago,
        )

        total_dwell_seconds = 0
        count = 0
        for entry in exited_vehicles:
            if entry.entry_time:
                dwell = (entry.exit_time - entry.entry_time).total_seconds()
                total_dwell_seconds += dwell
                count += 1

        avg_dwell_hours = (
            round(total_dwell_seconds / count / 3600, 1) if count > 0 else 0
        )

        return {
            "total_on_terminal": total_on_terminal,
            "avg_dwell_hours": avg_dwell_hours,
            "by_type": by_type,
        }

    def _get_preorder_stats(self) -> dict:
        """Get pre-order statistics."""
        today = timezone.now().date()

        stats = PreOrder.objects.aggregate(
            pending=Count("id", filter=Q(status="PENDING")),
            matched=Count("id", filter=Q(status="MATCHED")),
            completed_today=Count(
                "id",
                filter=Q(status="COMPLETED") & Q(matched_at__date=today),
            ),
        )

        return {
            "pending": stats["pending"],
            "matched": stats["matched"],
            "completed_today": stats["completed_today"],
        }
