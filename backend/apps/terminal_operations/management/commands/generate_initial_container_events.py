"""
Management command to generate initial events for existing containers.

This is a one-time migration to backfill event history for containers
that existed before the event tracking system was implemented.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.terminal_operations.models import ContainerEntry, ContainerEvent, CraneOperation
from apps.terminal_operations.services import ContainerEventService


class Command(BaseCommand):
    help = "Generate initial events for existing container entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be created, don't actually create events",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of containers to process per batch (default: 100)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No events will be created"))

        event_service = ContainerEventService()

        # Get entries without any events
        entries_without_events = ContainerEntry.objects.exclude(
            id__in=ContainerEvent.objects.values_list("container_entry_id", flat=True)
        ).select_related("container", "recorded_by").prefetch_related("crane_operations")

        total_entries = entries_without_events.count()
        self.stdout.write(f"Found {total_entries} container entries without events")

        if total_entries == 0:
            self.stdout.write(self.style.SUCCESS("No entries to process"))
            return

        # Counters
        entry_created_count = 0
        position_assigned_count = 0
        exit_recorded_count = 0
        crane_operation_count = 0

        # Process in batches
        processed = 0
        for entry in entries_without_events.iterator(chunk_size=batch_size):
            if not dry_run:
                with transaction.atomic():
                    # 1. Create ENTRY_CREATED event
                    event_service.create_entry_created_event(
                        container_entry=entry,
                        performed_by=entry.recorded_by,
                        source="SYSTEM",
                    )
                    entry_created_count += 1

                    # 2. Create POSITION_ASSIGNED event if has position
                    if hasattr(entry, "position") and entry.position:
                        pos = entry.position
                        event_service.create_position_assigned_event(
                            container_entry=entry,
                            zone=pos.zone,
                            row=pos.row,
                            bay=pos.bay,
                            tier=pos.tier,
                            sub_slot=pos.sub_slot,
                            auto_assigned=pos.auto_assigned,
                            source="SYSTEM",
                        )
                        position_assigned_count += 1

                    # 3. Create EXIT_RECORDED event if has exit_date
                    if entry.exit_date:
                        event_service.create_exit_recorded_event(
                            container_entry=entry,
                            source="SYSTEM",
                        )
                        exit_recorded_count += 1

                    # 4. Create CRANE_OPERATION events for each crane operation
                    for crane_op in entry.crane_operations.all():
                        event_service.create_crane_operation_event(
                            container_entry=entry,
                            operation_date=crane_op.operation_date,
                            crane_operation_id=crane_op.id,
                            source="SYSTEM",
                        )
                        crane_operation_count += 1
            else:
                # Dry run - just count
                entry_created_count += 1
                if hasattr(entry, "position") and entry.position:
                    position_assigned_count += 1
                if entry.exit_date:
                    exit_recorded_count += 1
                crane_operation_count += entry.crane_operations.count()

            processed += 1
            if processed % batch_size == 0:
                self.stdout.write(f"Processed {processed}/{total_entries} entries...")

        # Summary
        total_events = entry_created_count + position_assigned_count + exit_recorded_count + crane_operation_count

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {entry_created_count} ENTRY_CREATED events")
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {position_assigned_count} POSITION_ASSIGNED events")
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {exit_recorded_count} EXIT_RECORDED events")
        self.stdout.write(f"{'Would create' if dry_run else 'Created'} {crane_operation_count} CRANE_OPERATION events")
        self.stdout.write(self.style.SUCCESS(f"Total: {total_events} events for {total_entries} containers"))
