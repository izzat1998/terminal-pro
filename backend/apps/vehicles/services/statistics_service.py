from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.core.services import BaseService

from ..models import VehicleEntry


class VehicleStatisticsService(BaseService):
    """
    Service for calculating vehicle terminal statistics
    """

    def get_current_statistics(self):
        """
        Get current vehicles on terminal with breakdowns

        Returns:
            dict with total count and breakdowns by type, transport, load status
        """
        on_terminal = VehicleEntry.objects.filter(status="ON_TERMINAL")

        # Total count
        total = on_terminal.count()

        # By vehicle type
        by_vehicle_type = {}
        vehicle_type_counts = on_terminal.values("vehicle_type").annotate(
            count=Count("id")
        )
        for item in vehicle_type_counts:
            vtype = item["vehicle_type"]
            label = dict(VehicleEntry.VEHICLE_TYPE_CHOICES).get(vtype, vtype)
            by_vehicle_type[vtype] = {"count": item["count"], "label": label}

        # By transport type (only for CARGO vehicles)
        by_transport_type = {}
        transport_counts = (
            on_terminal.filter(vehicle_type="CARGO", transport_type__isnull=False)
            .values("transport_type")
            .annotate(count=Count("id"))
        )
        for item in transport_counts:
            ttype = item["transport_type"]
            label = dict(VehicleEntry.TRANSPORT_TYPE_CHOICES).get(ttype, ttype)
            by_transport_type[ttype] = {"count": item["count"], "label": label}

        # By load status (only for CARGO vehicles with load status)
        by_load_status = {}
        load_counts = (
            on_terminal.filter(vehicle_type="CARGO", entry_load_status__isnull=False)
            .values("entry_load_status")
            .annotate(count=Count("id"))
        )
        for item in load_counts:
            lstatus = item["entry_load_status"]
            label = dict(VehicleEntry.LOAD_STATUS_CHOICES).get(lstatus, lstatus)
            by_load_status[lstatus] = {"count": item["count"], "label": label}

        return {
            "total_on_terminal": total,
            "by_vehicle_type": by_vehicle_type,
            "by_transport_type": by_transport_type,
            "by_load_status": by_load_status,
        }

    def get_time_metrics(self):
        """
        Get dwell time metrics

        Returns:
            dict with average dwell time and longest current stay
        """
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Average dwell time from exited vehicles in last 30 days
        # Exclude entries with null entry_time (data integrity issue)
        exited_vehicles = VehicleEntry.objects.filter(
            exit_time__isnull=False,
            entry_time__isnull=False,
            exit_time__gte=thirty_days_ago,
        )

        # Calculate average dwell in Python (more reliable than DB-level timedelta)
        total_dwell_seconds = 0
        count = 0
        dwell_by_type = {"LIGHT": [], "CARGO": []}

        for entry in exited_vehicles:
            # Skip entries where entry_time is None (data integrity issue)
            if entry.entry_time is None:
                continue
            dwell = (entry.exit_time - entry.entry_time).total_seconds()
            total_dwell_seconds += dwell
            count += 1
            if entry.vehicle_type in dwell_by_type:
                dwell_by_type[entry.vehicle_type].append(dwell)

        avg_dwell_hours = (
            round(total_dwell_seconds / count / 3600, 1) if count > 0 else 0
        )

        # Average by type
        avg_dwell_by_type = {}
        for vtype, dwells in dwell_by_type.items():
            if dwells:
                avg_dwell_by_type[vtype] = round(sum(dwells) / len(dwells) / 3600, 1)
            else:
                avg_dwell_by_type[vtype] = 0

        # Longest current stay - always return structure for frontend consistency
        longest_stay = {"license_plate": "", "hours": "", "vehicle_type": ""}
        on_terminal = (
            VehicleEntry.objects.filter(status="ON_TERMINAL", entry_time__isnull=False)
            .order_by("entry_time")
            .first()
        )
        if on_terminal and on_terminal.entry_time:
            hours = (now - on_terminal.entry_time).total_seconds() / 3600
            longest_stay = {
                "license_plate": on_terminal.license_plate,
                "hours": round(hours, 1),
                "vehicle_type": on_terminal.vehicle_type,
            }

        return {
            "avg_dwell_hours": avg_dwell_hours,
            "avg_dwell_by_type": avg_dwell_by_type,
            "longest_current_stay": longest_stay,
        }

    def get_overstayers(self, threshold_hours=24):
        """
        Get vehicles that have been on terminal longer than threshold

        Args:
            threshold_hours: Number of hours after which a vehicle is considered overstaying

        Returns:
            dict with threshold, count, and list of overstaying vehicles
        """
        now = timezone.now()
        threshold_time = now - timedelta(hours=threshold_hours)

        overstayers = VehicleEntry.objects.filter(
            status="ON_TERMINAL", entry_time__lt=threshold_time
        ).order_by("entry_time")

        vehicles = []
        for entry in overstayers:
            hours = (now - entry.entry_time).total_seconds() / 3600
            vehicles.append(
                {
                    "license_plate": entry.license_plate,
                    "hours": round(hours, 1),
                    "vehicle_type": entry.vehicle_type,
                }
            )

        return {
            "threshold_hours": threshold_hours,
            "count": len(vehicles),
            "vehicles": vehicles,
        }

    def get_historical_statistics(self, days=30):
        """
        Get historical entry/exit statistics

        Args:
            days: Number of days to look back

        Returns:
            dict with total entries, exits, and daily breakdown
        """
        now = timezone.now()
        start_date = now - timedelta(days=days)

        # Total entries in period
        total_entries = VehicleEntry.objects.filter(entry_time__gte=start_date).count()

        # Total exits in period
        total_exits = VehicleEntry.objects.filter(
            exit_time__isnull=False, exit_time__gte=start_date
        ).count()

        # Entries by day
        entries_by_day = (
            VehicleEntry.objects.filter(entry_time__gte=start_date)
            .annotate(date=TruncDate("entry_time"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        daily_data = [
            {"date": item["date"].isoformat(), "count": item["count"]}
            for item in entries_by_day
        ]

        return {
            "total_entries": total_entries,
            "total_exits": total_exits,
            "entries_by_day": daily_data,
        }

    def get_all_statistics(self, overstayer_hours=24):
        """
        Get all statistics in one call

        Args:
            overstayer_hours: Threshold for overstayer detection

        Returns:
            dict with all statistics sections
        """
        return {
            "current": self.get_current_statistics(),
            "time_metrics": self.get_time_metrics(),
            "overstayers": self.get_overstayers(overstayer_hours),
            "last_30_days": self.get_historical_statistics(30),
        }
