"""
Management command to fix VehicleEntry statuses based on entry/exit times.
Run this after deploying the status field to update existing records.

Usage:
    python manage.py fix_vehicle_statuses          # Dry run (preview changes)
    python manage.py fix_vehicle_statuses --apply  # Apply changes
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.vehicles.models import VehicleEntry


class Command(BaseCommand):
    help = "Fix VehicleEntry statuses based on entry_time and exit_time"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (without this flag, only shows preview)",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "\n=== DRY RUN MODE (use --apply to save changes) ===\n"
                )
            )

        # Get all vehicle entries
        entries = VehicleEntry.objects.all()
        total = entries.count()

        self.stdout.write(f"Total VehicleEntry records: {total}\n")

        # Counters
        to_exited = []
        to_on_terminal = []
        to_waiting = []
        already_correct = 0

        for entry in entries:
            expected_status = self._determine_status(entry)

            if entry.status == expected_status:
                already_correct += 1
                continue

            change_info = {
                "id": entry.id,
                "plate": entry.license_plate,
                "current": entry.status,
                "new": expected_status,
                "entry_time": entry.entry_time,
                "exit_time": entry.exit_time,
            }

            if expected_status == "EXITED":
                to_exited.append(change_info)
            elif expected_status == "ON_TERMINAL":
                to_on_terminal.append(change_info)
            elif expected_status == "WAITING":
                to_waiting.append(change_info)

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Already correct: {already_correct}")
        self.stdout.write(f"To be changed to EXITED: {len(to_exited)}")
        self.stdout.write(f"To be changed to ON_TERMINAL: {len(to_on_terminal)}")
        self.stdout.write(f"To be changed to WAITING: {len(to_waiting)}")
        self.stdout.write("=" * 60 + "\n")

        # Print details
        if to_exited:
            self.stdout.write(self.style.SUCCESS("\n--- WILL SET TO EXITED ---"))
            for item in to_exited[:10]:  # Show first 10
                self.stdout.write(
                    f"  ID: {item['id']}, Plate: {item['plate']}, "
                    f"Current: {item['current']} -> EXITED "
                    f"(exit_time: {item['exit_time']})"
                )
            if len(to_exited) > 10:
                self.stdout.write(f"  ... and {len(to_exited) - 10} more")

        if to_on_terminal:
            self.stdout.write(self.style.WARNING("\n--- WILL SET TO ON_TERMINAL ---"))
            for item in to_on_terminal[:10]:
                self.stdout.write(
                    f"  ID: {item['id']}, Plate: {item['plate']}, "
                    f"Current: {item['current']} -> ON_TERMINAL "
                    f"(entry_time: {item['entry_time']}, no exit)"
                )
            if len(to_on_terminal) > 10:
                self.stdout.write(f"  ... and {len(to_on_terminal) - 10} more")

        if to_waiting:
            self.stdout.write(self.style.NOTICE("\n--- WILL SET TO WAITING ---"))
            for item in to_waiting[:10]:
                self.stdout.write(
                    f"  ID: {item['id']}, Plate: {item['plate']}, "
                    f"Current: {item['current']} -> WAITING (no entry_time)"
                )
            if len(to_waiting) > 10:
                self.stdout.write(f"  ... and {len(to_waiting) - 10} more")

        # Apply changes if requested
        if apply_changes:
            self.stdout.write("\n" + self.style.HTTP_INFO("Applying changes..."))

            with transaction.atomic():
                updated_count = 0

                # Update to EXITED
                if to_exited:
                    ids = [item["id"] for item in to_exited]
                    count = VehicleEntry.objects.filter(id__in=ids).update(
                        status="EXITED"
                    )
                    updated_count += count
                    self.stdout.write(f"  Updated {count} records to EXITED")

                # Update to ON_TERMINAL
                if to_on_terminal:
                    ids = [item["id"] for item in to_on_terminal]
                    count = VehicleEntry.objects.filter(id__in=ids).update(
                        status="ON_TERMINAL"
                    )
                    updated_count += count
                    self.stdout.write(f"  Updated {count} records to ON_TERMINAL")

                # Update to WAITING
                if to_waiting:
                    ids = [item["id"] for item in to_waiting]
                    count = VehicleEntry.objects.filter(id__in=ids).update(
                        status="WAITING"
                    )
                    updated_count += count
                    self.stdout.write(f"  Updated {count} records to WAITING")

            self.stdout.write(
                self.style.SUCCESS(f"\nDone! Updated {updated_count} records.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nNo changes applied. Run with --apply to update records."
                )
            )

    def _determine_status(self, entry):
        """
        Determine what the status should be based on entry/exit times.

        Logic:
        - exit_time is set -> EXITED
        - entry_time is set, exit_time is None -> ON_TERMINAL
        - entry_time is None -> WAITING
        """
        if entry.exit_time:
            return "EXITED"
        elif entry.entry_time:
            return "ON_TERMINAL"
        else:
            return "WAITING"
