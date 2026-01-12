"""
Django management command to safely delete container entries created by bulk Excel import
on a specific date/time.

Usage:
    # Preview what will be deleted (dry run - safe)
    python manage.py delete_bulk_import --dry-run

    # Actually delete the entries (requires confirmation)
    python manage.py delete_bulk_import

    # Delete without confirmation prompt (DANGEROUS - use with caution)
    python manage.py delete_bulk_import --no-confirm
"""

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.terminal_operations.models import ContainerEntry


class Command(BaseCommand):
    help = "Delete container entries created on November 3, 2025 at 12:31 (Excel import batch)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what will be deleted without actually deleting",
        )
        parser.add_argument(
            "--no-confirm",
            action="store_true",
            help="Skip confirmation prompt (DANGEROUS)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        no_confirm = options["no_confirm"]

        # Target datetime: November 3, 2025 at 12:31 (Tashkent timezone)
        target_date = timezone.make_aware(
            datetime.datetime(2025, 11, 3, 12, 31, 0), timezone.get_current_timezone()
        )

        # Find entries created within a 1-minute window (12:31:00 - 12:31:59)
        start_time = target_date
        end_time = target_date + datetime.timedelta(minutes=1)

        self.stdout.write(
            self.style.WARNING(
                f"\n{'=' * 70}\n"
                f"SEARCHING FOR ENTRIES CREATED BETWEEN:\n"
                f"  Start: {start_time}\n"
                f"  End:   {end_time}\n"
                f"{'=' * 70}\n"
            )
        )

        # Query entries created in this time window
        entries_to_delete = ContainerEntry.objects.filter(
            created_at__gte=start_time, created_at__lt=end_time
        ).select_related("container", "recorded_by", "container_owner")

        count = entries_to_delete.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ No entries found matching the criteria. Nothing to delete.\n"
                )
            )
            return

        # Display detailed information about what will be deleted
        self.stdout.write(self.style.WARNING(f"\nFound {count} entries to delete:\n"))

        for i, entry in enumerate(entries_to_delete[:20], 1):  # Show first 20
            self.stdout.write(
                f"  {i}. {entry.container.container_number} | "
                f"Entry: {entry.entry_time.strftime('%Y-%m-%d %H:%M')} | "
                f"Created: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Status: {entry.get_status_display()} | "
                f"Transport: {entry.get_transport_type_display()}"
            )

        if count > 20:
            self.stdout.write(f"  ... and {count - 20} more entries\n")

        # Show summary statistics
        self.stdout.write(
            self.style.WARNING(
                f"\n{'=' * 70}\nSUMMARY:\n  Total entries: {count}\n{'=' * 70}\n"
            )
        )

        # Dry run mode - just preview, don't delete
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ DRY RUN MODE - No entries were deleted.\n"
                    "Run without --dry-run to actually delete these entries.\n"
                )
            )
            return

        # Confirmation prompt (unless --no-confirm flag is used)
        if not no_confirm:
            self.stdout.write(
                self.style.ERROR(
                    f"\n⚠ WARNING: This will permanently delete {count} container entries!\n"
                )
            )
            confirm = input('Type "DELETE" to confirm deletion: ')

            if confirm != "DELETE":
                self.stdout.write(
                    self.style.WARNING(
                        "\n✗ Deletion cancelled. No changes were made.\n"
                    )
                )
                return

        # Perform deletion
        self.stdout.write(self.style.WARNING("\nDeleting entries...\n"))

        deleted_count, deleted_details = entries_to_delete.delete()

        # Show deletion results
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 70}\n"
                f"DELETION COMPLETE:\n"
                f"  Container entries deleted: {deleted_count}\n"
                f"{'=' * 70}\n"
            )
        )

        # Show related objects that were also deleted (CASCADE)
        if deleted_details:
            self.stdout.write("\nRelated objects deleted:")
            for model, count in deleted_details.items():
                if count > 0:
                    self.stdout.write(f"  - {model}: {count}")

        self.stdout.write(self.style.SUCCESS("\n✓ Done!\n"))
