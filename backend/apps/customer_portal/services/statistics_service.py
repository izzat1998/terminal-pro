"""
Service for calculating customer container statistics.

Follows MTT's service layer pattern - all business logic here, views are thin.
"""

from django.db.models import Avg, Count, ExpressionWrapper, F, Sum, fields
from django.db.models.functions import Coalesce, Now
from django.utils import timezone

from apps.core.services.base_service import BaseService
from apps.terminal_operations.models import ContainerEntry


class CustomerStatisticsService(BaseService):
    """Service for calculating customer container statistics."""

    def __init__(self, company):
        super().__init__()
        self.company = company

    def _get_active_entries(self):
        """Get entries currently on terminal (no exit_date)."""
        return ContainerEntry.objects.filter(company=self.company, exit_date__isnull=True)

    def _annotate_dwell_days(self, queryset):
        """Annotate queryset with calculated dwell_days field."""
        return queryset.annotate(
            dwell_days=ExpressionWrapper(
                (Coalesce(F("exit_date"), Now()) - F("entry_time")),
                output_field=fields.DurationField(),
            )
        )

    def get_status_summary(self) -> dict:
        """Get current container status breakdown."""
        active = self._get_active_entries()
        total = active.count()

        status_counts = active.values("status").annotate(count=Count("id"))
        transport_counts = active.values("transport_type").annotate(count=Count("id"))

        return {
            "total_on_terminal": total,
            "by_status": {item["status"]: item["count"] for item in status_counts},
            "by_transport": {item["transport_type"]: item["count"] for item in transport_counts},
        }

    def get_dwell_metrics(self, overstayer_days: int = 7) -> dict:
        """Get dwell time statistics."""
        active = self._get_active_entries().select_related("container")
        now = timezone.now()

        # Calculate dwell time in Python for each entry
        entries_with_dwell = []
        for entry in active:
            dwell = (now - entry.entry_time).days
            entries_with_dwell.append(
                {
                    "entry": entry,
                    "dwell_days": dwell,
                }
            )

        # Calculate average
        if entries_with_dwell:
            avg_dwell = sum(e["dwell_days"] for e in entries_with_dwell) / len(entries_with_dwell)
        else:
            avg_dwell = 0

        # Filter overstayers
        overstayers = [e for e in entries_with_dwell if e["dwell_days"] > overstayer_days]
        overstayers.sort(key=lambda x: x["dwell_days"], reverse=True)

        overstayer_list = [
            {
                "id": e["entry"].id,
                "container__container_number": e["entry"].container.container_number,
                "dwell_time_days": e["dwell_days"],
            }
            for e in overstayers[:5]
        ]

        # Longest stay
        longest = max(entries_with_dwell, key=lambda x: x["dwell_days"]) if entries_with_dwell else None

        return {
            "average_dwell_days": round(avg_dwell, 1),
            "overstayer_count": len(overstayers),
            "overstayer_threshold_days": overstayer_days,
            "overstayers": overstayer_list,
            "longest_stay": (
                {
                    "container_number": longest["entry"].container.container_number,
                    "days": longest["dwell_days"],
                }
                if longest
                else None
            ),
        }

    def get_cargo_summary(self) -> dict:
        """Get cargo weight statistics."""
        active = self._get_active_entries().filter(status="LADEN")

        aggregates = active.aggregate(
            total_weight=Sum("cargo_weight"),
            avg_weight=Avg("cargo_weight"),
            count=Count("id"),
        )

        return {
            "laden_count": aggregates["count"] or 0,
            "total_weight_kg": float(aggregates["total_weight"] or 0),
            "average_weight_kg": round(float(aggregates["avg_weight"] or 0), 1),
        }

    def get_all_statistics(self) -> dict:
        """Get consolidated statistics."""
        return {
            "status": self.get_status_summary(),
            "dwell": self.get_dwell_metrics(),
            "cargo": self.get_cargo_summary(),
            "generated_at": timezone.now().isoformat(),
        }
