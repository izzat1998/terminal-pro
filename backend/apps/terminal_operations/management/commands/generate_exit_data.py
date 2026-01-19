"""
Generate realistic exit data for existing containers.

Adds exit_date and exit transport info to a percentage of containers
to create realistic entry/exit patterns for dashboard visualization.

Usage:
    python manage.py generate_exit_data              # Default: 40% of containers exit
    python manage.py generate_exit_data --percent 60 # 60% exit
    python manage.py generate_exit_data --days 30    # Spread exits over 30 days
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.terminal_operations.models import ContainerEntry


# =============================================================================
# EXIT DATA CONSTANTS
# =============================================================================

# Exit transport type distribution
EXIT_TRANSPORT_WEIGHTS = [
    ("TRUCK", 75),  # Most containers leave by truck
    ("WAGON", 20),  # Some by rail wagon
    ("TRAIN", 5),  # Few by full train
]

# Destination stations (Uzbekistan and neighboring countries)
DESTINATION_STATIONS = [
    "Тошкент-Товарный",
    "Сергели",
    "Чукурсай",
    "Самарканд",
    "Бухоро",
    "Навои",
    "Карши",
    "Термез",
    "Андижон",
    "Фергана",
    "Алмалык",
    "Чирчик",
    "Олмалиқ",
    # Neighboring countries
    "Достык (KZ)",
    "Хайратон (AF)",
    "Сарыагаш (KZ)",
]

# Uzbek vehicle plate patterns for exit trucks
UZ_REGIONS = ["01", "10", "20", "30", "40", "50", "60", "70", "80", "90"]


class Command(BaseCommand):
    help = "Generate realistic exit data for containers on terminal"

    def add_arguments(self, parser):
        parser.add_argument(
            "--percent",
            type=int,
            default=40,
            help="Percentage of containers to mark as exited (default: 40)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to spread exits over (default: 30)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing exit data first (reset all containers to on-terminal)",
        )

    def handle(self, *args, **options):
        exit_percent = options["percent"]
        days_spread = options["days"]

        self.stdout.write(
            self.style.MIGRATE_HEADING("\n📦 Generating Exit Data for Containers")
        )
        self.stdout.write(f"   Exit percentage: {exit_percent}%")
        self.stdout.write(f"   Days spread: {days_spread} days\n")

        with transaction.atomic():
            if options["clear"]:
                self._clear_exit_data()

            # Get containers still on terminal
            on_terminal = ContainerEntry.objects.filter(exit_date__isnull=True)
            total_on_terminal = on_terminal.count()

            if total_on_terminal == 0:
                self.stdout.write(
                    self.style.WARNING("   No containers on terminal to process!")
                )
                return

            # Calculate how many to exit
            target_exits = int(total_on_terminal * exit_percent / 100)

            self.stdout.write("📊 Container Status:")
            self.stdout.write(f"   Currently on terminal: {total_on_terminal}")
            self.stdout.write(f"   Target exits ({exit_percent}%): {target_exits}")

            # Select random containers to exit
            container_ids = list(on_terminal.values_list("id", flat=True))
            exit_ids = random.sample(
                container_ids, min(target_exits, len(container_ids))
            )

            # Generate exit data
            self._generate_exits(exit_ids, days_spread)

            # Print summary
            self._print_summary()

    def _clear_exit_data(self):
        """Reset all containers to on-terminal status."""
        self.stdout.write("\n🔄 Clearing existing exit data...")

        updated = ContainerEntry.objects.filter(exit_date__isnull=False).update(
            exit_date=None,
            exit_transport_type="",
            exit_train_number="",
            exit_transport_number="",
            destination_station="",
        )

        self.stdout.write(f"   Reset {updated} containers to on-terminal status")

    def _generate_exits(self, container_ids: list, days_spread: int):
        """Generate realistic exit data for selected containers."""
        self.stdout.write(f"\n🚪 Processing {len(container_ids)} container exits...")

        now = timezone.now()

        # Build weighted transport type list
        transport_types = []
        for transport_type, weight in EXIT_TRANSPORT_WEIGHTS:
            transport_types.extend([transport_type] * weight)

        exits_by_day = {}
        processed = 0
        positions_removed = 0

        for container_id in container_ids:
            try:
                entry = ContainerEntry.objects.get(id=container_id)

                # Calculate exit date: must be after entry_time
                # Random day within the spread, but not before entry
                min_dwell_hours = 4  # Minimum 4 hours on terminal
                max_days_ago = min(days_spread, (now - entry.entry_time).days - 1)

                if max_days_ago < 0:
                    # Container entered too recently, skip
                    continue

                # Weight towards more recent exits (bell curve)
                days_ago = self._weighted_random_days(max_days_ago)
                exit_time = now - timedelta(days=days_ago)

                # Ensure exit is after entry
                if exit_time <= entry.entry_time:
                    exit_time = entry.entry_time + timedelta(hours=min_dwell_hours)

                # Track exits by day for reporting
                day_key = exit_time.date().isoformat()
                exits_by_day[day_key] = exits_by_day.get(day_key, 0) + 1

                # Generate exit transport data
                transport_type = random.choice(transport_types)
                exit_data = {
                    "exit_date": exit_time,
                    "exit_transport_type": transport_type,
                    "destination_station": random.choice(DESTINATION_STATIONS),
                }

                # Add transport number based on type
                if transport_type == "TRUCK":
                    exit_data["exit_transport_number"] = self._generate_truck_plate()
                elif transport_type == "WAGON":
                    exit_data["exit_transport_number"] = self._generate_wagon_number()
                    exit_data["exit_train_number"] = f"#{random.randint(100, 999)}"
                elif transport_type == "TRAIN":
                    exit_data["exit_train_number"] = f"T-{random.randint(1000, 9999)}"

                # Update the entry
                for key, value in exit_data.items():
                    setattr(entry, key, value)
                entry.save()

                # Remove 3D position (exited containers shouldn't be on yard)
                if hasattr(entry, "position"):
                    entry.position.delete()
                    positions_removed += 1

                processed += 1

            except ContainerEntry.DoesNotExist:
                continue

        self.stdout.write(f"   ✓ Processed {processed} exits")
        self.stdout.write(f"   ✓ Removed {positions_removed} 3D positions")

        # Show exit distribution
        if exits_by_day:
            self.stdout.write("\n📅 Exit Distribution (last 10 days):")
            sorted_days = sorted(exits_by_day.items(), reverse=True)[:10]
            for day, count in sorted_days:
                bar = "█" * min(count, 20)
                self.stdout.write(f"   {day}: {bar} {count}")

    def _weighted_random_days(self, max_days: int) -> int:
        """Generate random days with weight towards recent dates."""
        if max_days <= 0:
            return 0

        # Create weights: more recent = higher weight
        # Using triangular distribution favoring recent dates
        weights = [max_days - i for i in range(max_days + 1)]
        days_list = list(range(max_days + 1))

        return random.choices(days_list, weights=weights, k=1)[0]

    def _generate_truck_plate(self) -> str:
        """Generate Uzbek-style truck plate number."""
        region = random.choice(UZ_REGIONS)
        letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=1))
        numbers = f"{random.randint(100, 999)}"
        suffix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        return f"{region}{letters}{numbers}{suffix}"

    def _generate_wagon_number(self) -> str:
        """Generate rail wagon number."""
        return f"{random.randint(50000000, 59999999)}"

    def _print_summary(self):
        """Print final summary."""
        on_terminal = ContainerEntry.objects.filter(exit_date__isnull=True).count()
        exited = ContainerEntry.objects.filter(exit_date__isnull=False).count()
        total = on_terminal + exited

        today = timezone.now().date()
        exited_today = ContainerEntry.objects.filter(exit_date__date=today).count()

        last_7_days = today - timedelta(days=7)
        exited_week = ContainerEntry.objects.filter(
            exit_date__date__gte=last_7_days
        ).count()

        self.stdout.write(self.style.SUCCESS("\n✅ Exit data generation complete!"))
        self.stdout.write("\n📊 Final Statistics:")
        self.stdout.write(f"   Total containers: {total}")
        self.stdout.write(
            f"   On terminal: {on_terminal} ({on_terminal * 100 // max(total, 1)}%)"
        )
        self.stdout.write(f"   Exited: {exited} ({exited * 100 // max(total, 1)}%)")
        self.stdout.write(f"   Exited today: {exited_today}")
        self.stdout.write(f"   Exited last 7 days: {exited_week}")
