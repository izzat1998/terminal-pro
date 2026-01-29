"""
Management command to create comprehensive test data for container full history.

Creates a single container with 4 entries to demonstrate:
- Multiple entries over time (re-entry scenarios)
- Different container owners between entries
- Different companies/clients
- Various cargo weights and destinations
- Different transport types (TRUCK, TRAIN)
- Status changes (LADEN, EMPTY)
- Position assignments
- Crane operations
- Complete lifecycle (entry → operations → exit)
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Company, CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import (
    ContainerEntry,
    ContainerEvent,
    ContainerOwner,
    ContainerPosition,
    CraneOperation,
)
from apps.terminal_operations.services import ContainerEventService


class Command(BaseCommand):
    help = "Create test data for container full history feature"

    def add_arguments(self, parser):
        parser.add_argument(
            "--container-number",
            type=str,
            default="TESU7654321",
            help="Container number to use (default: TESU7654321)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove existing test data before creating new",
        )

    def handle(self, *args, **options):
        container_number = options["container_number"]
        clean = options["clean"]

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Creating History Test Data for: {container_number}")
        self.stdout.write(f"{'='*60}\n")

        # Get or create prerequisites
        owners = list(ContainerOwner.objects.all()[:5])
        if len(owners) < 3:
            self.stdout.write(self.style.ERROR("Need at least 3 container owners. Run seed_data first."))
            return

        companies = list(Company.objects.all()[:5])
        if len(companies) < 3:
            self.stdout.write(self.style.ERROR("Need at least 3 companies. Run seed_data first."))
            return

        managers = list(CustomUser.objects.filter(user_type="manager", is_active=True)[:5])
        if not managers:
            managers = list(CustomUser.objects.filter(is_active=True)[:5])
        if not managers:
            self.stdout.write(self.style.ERROR("Need at least 1 active user. Run seed_data first."))
            return

        event_service = ContainerEventService()

        with transaction.atomic():
            # Clean existing test data if requested
            if clean:
                existing = Container.objects.filter(container_number=container_number).first()
                if existing:
                    ContainerEntry.objects.filter(container=existing).delete()
                    existing.delete()
                    self.stdout.write(f"Cleaned existing data for {container_number}")

            # Create the test container
            container, created = Container.objects.get_or_create(
                container_number=container_number,
                defaults={"iso_type": "22G1"},
            )
            self.stdout.write(f"{'Created' if created else 'Using existing'} container: {container_number}")

            now = timezone.now()

            # ============================================================
            # ENTRY 1: 6 months ago - LADEN, Maersk, via TRUCK, completed
            # ============================================================
            entry1_time = now - timedelta(days=180)
            entry1_exit = entry1_time + timedelta(days=15)

            entry1 = ContainerEntry.objects.create(
                container=container,
                container_owner=owners[0],  # Maersk Line
                company=companies[0],
                status="LADEN",
                transport_type="TRUCK",
                transport_number="01A777BB",
                entry_time=entry1_time,
                entry_train_number="",
                cargo_name="Электроника Samsung",
                cargo_weight=18500,
                client_name="Samsung Uzbekistan",
                destination_station="Ташкент-Товарная",
                recorded_by=managers[0],
                exit_date=entry1_exit,
                exit_transport_type="TRAIN",
                exit_transport_number="",
                exit_train_number="3456",
                note="Первый заезд контейнера",
            )

            # Events for Entry 1 (historical - no actual position, just event record)
            event_service.create_entry_created_event(entry1, managers[0], "TELEGRAM_BOT")

            # Position was assigned but container has exited - record event only
            event_service.create_position_assigned_event(
                entry1, "A", 1, 5, 1, "A", auto_assigned=True, source="SYSTEM"
            )

            crane1 = CraneOperation.objects.create(
                container_entry=entry1,
                operation_date=entry1_time + timedelta(hours=2),
            )
            event_service.create_crane_operation_event(
                entry1, crane1.operation_date, crane1.id, source="TELEGRAM_BOT"
            )

            event_service.create_exit_recorded_event(entry1, managers[0], "TELEGRAM_BOT")

            self.stdout.write(self.style.SUCCESS(
                f"  Entry 1: {entry1_time.date()} - {entry1_exit.date()} | "
                f"LADEN | {owners[0].name} | {companies[0].name}"
            ))

            # ============================================================
            # ENTRY 2: 4 months ago - EMPTY, MSC (different owner!), via TRAIN
            # ============================================================
            entry2_time = now - timedelta(days=120)
            entry2_exit = entry2_time + timedelta(days=10)

            entry2 = ContainerEntry.objects.create(
                container=container,
                container_owner=owners[1],  # MSC - Different owner!
                company=companies[1],  # Different company
                status="EMPTY",
                transport_type="TRAIN",
                transport_number="",
                entry_time=entry2_time,
                entry_train_number="7890",
                cargo_name="",
                cargo_weight=None,
                client_name="Empty Return",
                destination_station="",
                recorded_by=managers[0],
                exit_date=entry2_exit,
                exit_transport_type="TRUCK",
                exit_transport_number="01B888CC",
                exit_train_number="",
                note="Возврат пустого контейнера. Сменился владелец!",
            )

            event_service.create_entry_created_event(entry2, managers[0], "EXCEL_IMPORT")

            # Position was assigned but container has exited - record event only
            event_service.create_position_assigned_event(
                entry2, "B", 3, 2, 2, "B", auto_assigned=False, performed_by=managers[0], source="API"
            )

            event_service.create_exit_recorded_event(entry2, managers[0], "API")

            self.stdout.write(self.style.SUCCESS(
                f"  Entry 2: {entry2_time.date()} - {entry2_exit.date()} | "
                f"EMPTY | {owners[1].name} | {companies[1].name}"
            ))

            # ============================================================
            # ENTRY 3: 2 months ago - LADEN, Maersk again, heavy cargo, 2 crane ops
            # ============================================================
            entry3_time = now - timedelta(days=60)
            entry3_exit = entry3_time + timedelta(days=25)

            entry3 = ContainerEntry.objects.create(
                container=container,
                container_owner=owners[0],  # Back to Maersk
                company=companies[0],  # Back to first company
                status="LADEN",
                transport_type="TRUCK",
                transport_number="01C999DD",
                entry_time=entry3_time,
                entry_train_number="",
                cargo_name="Тяжелое оборудование",
                cargo_weight=28000,  # Heavy cargo!
                client_name="Uzbekistan Heavy Industries",
                destination_station="Андижан",
                recorded_by=managers[1] if len(managers) > 1 else managers[0],
                exit_date=entry3_exit,
                exit_transport_type="TRAIN",
                exit_transport_number="",
                exit_train_number="5678",
                additional_crane_operation_date=entry3_time + timedelta(days=5),
                note="Тяжёлый груз - потребовалась дополнительная крановая операция",
            )

            event_service.create_entry_created_event(entry3, managers[0], "TELEGRAM_BOT")

            # Position was assigned but container has exited - record event only
            event_service.create_position_assigned_event(
                entry3, "C", 1, 1, 1, "A", auto_assigned=True, source="SYSTEM"
            )

            # First crane operation
            crane3a = CraneOperation.objects.create(
                container_entry=entry3,
                operation_date=entry3_time + timedelta(hours=1),
            )
            event_service.create_crane_operation_event(
                entry3, crane3a.operation_date, crane3a.id, source="TELEGRAM_BOT"
            )

            # Additional crane operation (repositioning)
            crane3b = CraneOperation.objects.create(
                container_entry=entry3,
                operation_date=entry3_time + timedelta(days=5),
            )
            event_service.create_crane_operation_event(
                entry3, crane3b.operation_date, crane3b.id, source="API"
            )

            event_service.create_exit_recorded_event(entry3, managers[0], "TELEGRAM_BOT")

            self.stdout.write(self.style.SUCCESS(
                f"  Entry 3: {entry3_time.date()} - {entry3_exit.date()} | "
                f"LADEN | {owners[0].name} | 2 crane ops | Heavy: 28t"
            ))

            # ============================================================
            # ENTRY 4: Current - LADEN, CMA CGM, still on terminal
            # ============================================================
            entry4_time = now - timedelta(days=5)

            entry4 = ContainerEntry.objects.create(
                container=container,
                container_owner=owners[2],  # CMA CGM - yet another owner!
                company=companies[2],  # Different company again
                status="LADEN",
                transport_type="TRUCK",
                transport_number="01D111EE",
                entry_time=entry4_time,
                entry_train_number="",
                cargo_name="Текстильные изделия",
                cargo_weight=12000,
                client_name="Tashkent Textile Group",
                destination_station="Бухара",
                recorded_by=managers[0],
                exit_date=None,  # Still on terminal!
                note="Текущий заезд - контейнер на терминале",
            )

            event_service.create_entry_created_event(entry4, managers[0], "TELEGRAM_BOT")

            # Find a free position for the current entry (still on terminal)
            # Use row 99, bay 99 which is unlikely to conflict
            try:
                ContainerPosition.objects.create(
                    container_entry=entry4,
                    zone="A",
                    row=99,
                    bay=99,
                    tier=1,
                    sub_slot="A",
                    auto_assigned=True,
                )
                event_service.create_position_assigned_event(
                    entry4, "A", 99, 99, 1, "A", auto_assigned=True, source="SYSTEM"
                )
            except Exception as e:
                # If position fails, just record the event without actual position
                self.stdout.write(self.style.WARNING(f"  Could not create position: {e}"))
                event_service.create_position_assigned_event(
                    entry4, "A", 99, 99, 1, "A", auto_assigned=True, source="SYSTEM"
                )

            crane4 = CraneOperation.objects.create(
                container_entry=entry4,
                operation_date=entry4_time + timedelta(hours=1),
            )
            event_service.create_crane_operation_event(
                entry4, crane4.operation_date, crane4.id, source="TELEGRAM_BOT"
            )

            self.stdout.write(self.style.SUCCESS(
                f"  Entry 4: {entry4_time.date()} - ON TERMINAL | "
                f"LADEN | {owners[2].name} | {companies[2].name}"
            ))

        # Summary
        total_entries = ContainerEntry.objects.filter(container=container).count()
        total_events = ContainerEvent.objects.filter(
            container_entry__container=container
        ).count()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"Created test data for {container_number}:"))
        self.stdout.write(f"  - {total_entries} container entries")
        self.stdout.write(f"  - {total_events} events total")
        self.stdout.write("")
        self.stdout.write("Test scenarios covered:")
        self.stdout.write("  ✓ Multiple entries (re-entry after exit)")
        self.stdout.write("  ✓ Different owners across entries (Maersk → MSC → Maersk → CMA CGM)")
        self.stdout.write("  ✓ Different companies/clients")
        self.stdout.write("  ✓ LADEN and EMPTY status")
        self.stdout.write("  ✓ TRUCK and TRAIN transport types")
        self.stdout.write("  ✓ Various cargo weights (empty, normal, heavy)")
        self.stdout.write("  ✓ Position assignments in different zones")
        self.stdout.write("  ✓ Multiple crane operations")
        self.stdout.write("  ✓ Complete lifecycle (entry → exit)")
        self.stdout.write("  ✓ Currently on terminal (no exit)")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"\nQuery this container via API or check events table.")
