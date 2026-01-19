"""
Generate 90 days of realistic operational data (v2) - assumes foundation data exists.

PREREQUISITES: Run 'python manage.py generate_foundation_data' first!

Key features:
- Sequential position allocation (tight company clusters)
- 100% placement success (no failed work orders)
- Complete lifecycle with PLACEMENT + RETRIEVAL work orders
- 80% density target (operational gaps)
- Proper 20ft/40ft slot logic and tier stacking physics
- Checkpointing: commits every N days to prevent data loss

Usage:
    python manage.py generate_realistic_data_v2                           # Generate 90 days
    python manage.py generate_realistic_data_v2 --days 30                 # Custom days
    python manage.py generate_realistic_data_v2 --clear                   # Clear operational data first
    python manage.py generate_realistic_data_v2 --checkpoint-every 10     # Commit every 10 days (default)
    python manage.py generate_realistic_data_v2 --dry-run                 # Simulate without saving
"""

import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Company, CustomerProfile, ManagerProfile
from apps.billing.models import Tariff, TariffRate
from apps.containers.models import Container
from apps.terminal_operations.models import (
    ContainerEntry,
    ContainerOwner,
    ContainerPosition,
    PreOrder,
    TerminalVehicle,
    WorkOrder,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Generate 90 days of realistic operational data (v2) - requires foundation data"

    # Row allocation for container type segregation
    # Generation: 65% 40ft, 35% 20ft; 60% EMPTY, 40% LADEN
    # → 40ft EMPTY: 39%, 40ft LADEN: 26%, 20ft EMPTY: 21%, 20ft LADEN: 14%
    # Note: 20ft containers use 2 slots per bay, so effective capacity is 2x
    ROW_ALLOCATION = {
        ('40ft', 'EMPTY'): [1, 2, 3, 4, 5],    # 42% capacity (200 positions)
        ('40ft', 'LADEN'): [6, 7, 8],          # 25% capacity (120 positions)
        ('20ft', 'EMPTY'): [9],                # 17% capacity (80 positions, 2 slots)
        ('20ft', 'LADEN'): [10],               # 17% capacity (80 positions, 2 slots)
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-mode",
            action="store_true",
            help="Generate clean test data: 80%% terminal capacity (384 placed) + 3 waiting for placement",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days to generate (default: 90)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing operational data before generation",
        )
        parser.add_argument(
            "--checkpoint-every",
            type=int,
            default=10,
            help="Commit transaction every N days (default: 10, 0 = no checkpointing)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate generation without saving to database",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed progress information",
        )

    def handle(self, *args, **options):
        self.verbosity = 2 if options["verbose"] else 1
        self.dry_run = options["dry_run"]
        days = options["days"]
        self.checkpoint_every = options["checkpoint_every"]
        test_mode = options["test_mode"]

        # Test mode: generate clean test data with specific placement state
        if test_mode:
            self._run_test_mode(options)
            return

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN MODE - No data will be saved\n"))

        self.stdout.write(
            self.style.NOTICE(f"🚀 Starting operational data generation (v2) for {days} days...\n")
        )

        # Check foundation data exists
        foundation_check = self._check_foundation_data()
        if not foundation_check["valid"]:
            self.stdout.write(self.style.ERROR("\n❌ Foundation data missing!\n"))
            for error in foundation_check["errors"]:
                self.stdout.write(self.style.ERROR(f"  • {error}"))
            self.stdout.write(self.style.WARNING("\nRun this first: python manage.py generate_foundation_data\n"))
            return

        if options["clear"] and not self.dry_run:
            self._clear_operational_data()

        # Initialize statistics
        self.stats = {
            "containers_created": 0,
            "entries_created": 0,
            "preorders_created": 0,
            "work_orders_placement": 0,
            "work_orders_retrieval": 0,
            "positions_created": 0,
            "exits_processed": 0,
        }

        try:
            # Phase 1: Load foundation data
            self._log_phase("Phase 1: Loading foundation data")
            foundation = self._load_foundation_data()

            # Phase 2: Container pool (500 containers to support high terminal density)
            self._log_phase("Phase 2: Creating container pool")
            container_pool = self._create_container_pool(500)

            # Phase 3: Space allocation
            self._log_phase("Phase 3: Initializing space allocation")
            state = self._initialize_state(foundation)

            # Phase 4: Chronological generation with checkpointing
            self._log_phase(f"Phase 4: Generating {days} days of operations")
            if self.checkpoint_every > 0:
                self.stdout.write(f"  💾 Checkpointing every {self.checkpoint_every} days")
            self._generate_timeline_with_checkpoints(days, foundation, container_pool, state)

            if self.dry_run:
                self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - No data saved\n"))

            # Final statistics
            self._print_statistics()

            # Verify placement integrity
            if not self.dry_run:
                self._verify_placements()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}\n"))
            raise

    def _run_test_mode(self, options):
        """
        Generate clean test data: ~80% terminal capacity + 3 waiting for placement.

        Container size segregation (same-size stacking only):
        - Rows 1-5: 40ft EMPTY (5 rows × 10 bays × 4 tiers = 200 positions)
        - Rows 6-8: 40ft LADEN (3 rows × 10 bays × 4 tiers = 120 positions)
        - Row 9: 20ft EMPTY (1 row × 10 bays × 4 tiers × 2 slots = 80 positions)
        - Row 10: 20ft LADEN (1 row × 10 bays × 4 tiers × 2 slots = 80 positions)

        Total capacity: 480 positions (40ft: 320, 20ft: 160)
        Target: 80% = 384 containers + 3 waiting
        """
        self.stdout.write(self.style.NOTICE("\n🧪 TEST MODE - Generating 80% capacity data...\n"))

        # Check foundation data
        foundation_check = self._check_foundation_data()
        if not foundation_check["valid"]:
            self.stdout.write(self.style.ERROR("\n❌ Foundation data missing!\n"))
            for error in foundation_check["errors"]:
                self.stdout.write(self.style.ERROR(f"  • {error}"))
            self.stdout.write(self.style.WARNING("\nRun this first: python manage.py generate_foundation_data\n"))
            return

        # Always clear in test mode for predictable results
        self._clear_operational_data()

        # Initialize stats
        self.stats = {
            "containers_created": 0, "entries_created": 0, "preorders_created": 0,
            "work_orders_placement": 0, "work_orders_retrieval": 0,
            "positions_created": 0, "exits_processed": 0,
        }

        foundation = self._load_foundation_data()
        container_pool = self._create_container_pool(500)  # Enough for 80% + buffer

        # Separate containers by size based on their ISO type
        containers_40ft = [c for c in container_pool if self._get_container_size(c.iso_type) == '40ft']
        containers_20ft = [c for c in container_pool if self._get_container_size(c.iso_type) == '20ft']

        self.stdout.write(f"  📦 Container pool: {len(containers_40ft)} × 40ft, {len(containers_20ft)} × 20ft")

        # Calculate capacity with proper size segregation
        # 40ft: Rows 1-8 = 8 rows × 10 bays × 4 tiers = 320 positions
        # 20ft: Rows 9-10 = 2 rows × 10 bays × 4 tiers × 2 slots = 160 positions
        capacity_40ft = 320
        capacity_20ft = 160
        total_capacity = capacity_40ft + capacity_20ft  # 480

        target_fill_rate = 0.80
        target_40ft = int(capacity_40ft * target_fill_rate)  # 256
        target_20ft = int(capacity_20ft * target_fill_rate)  # 128

        self.stdout.write(f"  📊 Terminal capacity: {total_capacity} positions (40ft: {capacity_40ft}, 20ft: {capacity_20ft})")
        self.stdout.write(f"  🎯 Target fill rate: {target_fill_rate*100:.0f}%")
        self.stdout.write(f"     • 40ft containers: {target_40ft}")
        self.stdout.write(f"     • 20ft containers: {target_20ft}")
        self.stdout.write(f"  ⏳ Waiting containers: 3\n")

        placed_40ft = 0
        placed_20ft = 0
        waiting_count = 0
        used_containers = set()

        # Row allocation for size/status segregation
        rows_40ft_empty = [1, 2, 3, 4, 5]  # 200 positions
        rows_40ft_laden = [6, 7, 8]        # 120 positions
        rows_20ft_empty = [9]              # 80 positions (2 slots per bay)
        rows_20ft_laden = [10]             # 80 positions (2 slots per bay)

        entry_time_base = timezone.now() - timedelta(days=30)

        with transaction.atomic():
            # ═══════════════════════════════════════════════════════════
            # PHASE 1A: Fill 40ft containers (rows 1-8)
            # ═══════════════════════════════════════════════════════════
            self.stdout.write("📦 Phase 1A: Filling 40ft container rows (1-8)...")

            container_40ft_iter = iter(containers_40ft)

            for row in rows_40ft_empty + rows_40ft_laden:
                if placed_40ft >= target_40ft:
                    break

                status = "EMPTY" if row in rows_40ft_empty else "LADEN"

                for bay in range(1, 11):  # Bays 1-10
                    if placed_40ft >= target_40ft:
                        break

                    for tier in range(1, 5):  # Tiers 1-4 (ground up)
                        if placed_40ft >= target_40ft:
                            break

                        # Get next 40ft container
                        container = next(container_40ft_iter, None)
                        if not container:
                            self.stdout.write(self.style.WARNING("  ⚠️  Ran out of 40ft containers"))
                            break

                        used_containers.add(container.id)

                        # Create entry and position
                        self._create_test_entry_with_position(
                            container=container,
                            row=row,
                            bay=bay,
                            tier=tier,
                            sub_slot="A",  # 40ft always uses slot A (occupies full bay)
                            status=status,
                            foundation=foundation,
                            entry_time_base=entry_time_base,
                        )
                        placed_40ft += 1

                        if placed_40ft % 50 == 0:
                            self.stdout.write(f"    ... placed {placed_40ft}/{target_40ft} 40ft")

            self.stdout.write(self.style.SUCCESS(f"  ✓ Placed {placed_40ft} × 40ft containers"))

            # ═══════════════════════════════════════════════════════════
            # PHASE 1B: Fill 20ft containers (rows 9-10, using A and B slots)
            # ═══════════════════════════════════════════════════════════
            self.stdout.write("\n📦 Phase 1B: Filling 20ft container rows (9-10)...")

            container_20ft_iter = iter(containers_20ft)

            for row in rows_20ft_empty + rows_20ft_laden:
                if placed_20ft >= target_20ft:
                    break

                status = "EMPTY" if row in rows_20ft_empty else "LADEN"

                for bay in range(1, 11):  # Bays 1-10
                    if placed_20ft >= target_20ft:
                        break

                    for tier in range(1, 5):  # Tiers 1-4 (ground up)
                        if placed_20ft >= target_20ft:
                            break

                        # 20ft containers: fill slot A first, then slot B
                        for sub_slot in ["A", "B"]:
                            if placed_20ft >= target_20ft:
                                break

                            container = next(container_20ft_iter, None)
                            if not container:
                                self.stdout.write(self.style.WARNING("  ⚠️  Ran out of 20ft containers"))
                                break

                            used_containers.add(container.id)

                            self._create_test_entry_with_position(
                                container=container,
                                row=row,
                                bay=bay,
                                tier=tier,
                                sub_slot=sub_slot,
                                status=status,
                                foundation=foundation,
                                entry_time_base=entry_time_base,
                            )
                            placed_20ft += 1

                            if placed_20ft % 25 == 0:
                                self.stdout.write(f"    ... placed {placed_20ft}/{target_20ft} 20ft")

            self.stdout.write(self.style.SUCCESS(f"  ✓ Placed {placed_20ft} × 20ft containers"))

            # ═══════════════════════════════════════════════════════════
            # PHASE 2: Create 3 containers waiting for placement
            # ═══════════════════════════════════════════════════════════
            self.stdout.write("\n⏳ Phase 2: Creating 3 containers waiting for placement...")

            # Mix of sizes and statuses for realistic testing
            waiting_specs = [
                ("40ft", "EMPTY"),
                ("20ft", "EMPTY"),
                ("40ft", "LADEN"),
            ]

            remaining_40ft = [c for c in containers_40ft if c.id not in used_containers]
            remaining_20ft = [c for c in containers_20ft if c.id not in used_containers]

            for size, status in waiting_specs:
                pool = remaining_40ft if size == "40ft" else remaining_20ft
                if not pool:
                    self.stdout.write(self.style.WARNING(f"  ⚠️  No {size} container available for waiting"))
                    continue

                container = pool.pop(0)
                used_containers.add(container.id)

                company = random.choice(foundation["companies"])
                recorded_by = random.choice(foundation["managers"])
                container_owner = random.choice(foundation["container_owners"])
                entry_time = timezone.now() - timedelta(hours=random.randint(1, 4))

                ContainerEntry.objects.create(
                    container=container,
                    entry_time=entry_time,
                    status=status,
                    transport_type="TRUCK",
                    transport_number=f"01X{random.randint(100, 999)}YZ",
                    recorded_by=recorded_by,
                    company=company,
                    container_owner=container_owner,
                    client_name=f"AWAITING PLACEMENT ({size})",
                )
                waiting_count += 1

            self.stdout.write(self.style.SUCCESS(f"  ✓ Created {waiting_count} containers waiting for placement"))

        # Summary
        total_placed = placed_40ft + placed_20ft
        fill_rate = total_placed / total_capacity * 100
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("🧪 TEST DATA GENERATED"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"\n  📊 Terminal Statistics:")
        self.stdout.write(f"     • Total capacity: {total_capacity} positions")
        self.stdout.write(f"     • Placed containers: {total_placed}")
        self.stdout.write(f"       - 40ft: {placed_40ft} (rows 1-8)")
        self.stdout.write(f"       - 20ft: {placed_20ft} (rows 9-10, slots A+B)")
        self.stdout.write(f"     • Fill rate: {fill_rate:.1f}%")
        self.stdout.write(f"\n  📋 Container Status:")
        self.stdout.write(f"     • With positions (placed): {total_placed}")
        self.stdout.write(f"     • Waiting for placement: {waiting_count}")
        self.stdout.write(f"     • Total entries: {total_placed + waiting_count}")
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60 + "\n"))

    def _create_test_entry_with_position(
        self,
        container: Container,
        row: int,
        bay: int,
        tier: int,
        sub_slot: str,
        status: str,
        foundation: Dict[str, Any],
        entry_time_base: datetime,
    ):
        """Helper to create a container entry with position and work order in test mode."""
        company = random.choice(foundation["companies"])
        recorded_by = random.choice(foundation["managers"])
        container_owner = random.choice(foundation["container_owners"])
        vehicle = random.choice(foundation["vehicles"])

        days_ago = random.randint(1, 30)
        entry_time = entry_time_base + timedelta(
            days=days_ago,
            hours=random.randint(6, 18),
            minutes=random.randint(0, 59)
        )

        region = random.choice(["01", "10", "20", "30"])
        transport_number = f"{region}{random.choice('ABCD')}{random.randint(100, 999)}{random.choice('EF')}{random.choice('GH')}"

        entry = ContainerEntry.objects.create(
            container=container,
            entry_time=entry_time,
            status=status,
            transport_type="TRUCK",
            transport_number=transport_number,
            recorded_by=recorded_by,
            company=company,
            container_owner=container_owner,
            client_name=random.choice([
                "Toshkent Savdo", "Navoiy Mining", "Buxoro Textile",
                "Samarqand Logistika", "Farg'ona Yuk"
            ]),
            location=f"A-R{row:02d}-B{bay:02d}-T{tier}-{sub_slot}",
        )

        work_order = WorkOrder.objects.create(
            container_entry=entry,
            operation_type="PLACEMENT",
            status="COMPLETED",
            assigned_to_vehicle=vehicle,
            created_by=recorded_by,
            target_zone="A",
            target_row=row,
            target_bay=bay,
            target_tier=tier,
            target_sub_slot=sub_slot,
            priority="NORMAL",
        )

        self._set_work_order_timestamps(work_order, entry_time, "COMPLETED")

        ContainerPosition.objects.create(
            container_entry=entry,
            zone="A",
            row=row,
            bay=bay,
            tier=tier,
            sub_slot=sub_slot,
            auto_assigned=True,
        )

    def _check_foundation_data(self) -> Dict[str, Any]:
        """Validate that all required foundation data exists"""
        errors = []

        # Check admin users
        if not User.objects.filter(user_type="admin", is_active=True).exists():
            errors.append("No admin users found")

        # Check companies
        company_count = Company.objects.filter(is_active=True).count()
        if company_count == 0:
            errors.append("No companies found")

        # Check managers
        if not User.objects.filter(user_type="manager", is_active=True).exists():
            errors.append("No manager users found")

        # Check customers
        if not User.objects.filter(user_type="customer", is_active=True).exists():
            errors.append("No customer users found")

        # Check container owners
        if not ContainerOwner.objects.exists():
            errors.append("No container owners found")

        # Check terminal vehicles
        if not TerminalVehicle.objects.filter(is_active=True).exists():
            errors.append("No terminal vehicles found")

        # Check tariffs
        if not Tariff.objects.exists():
            errors.append("No tariffs found")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def _clear_operational_data(self):
        """Clear operational data while preserving foundation data"""
        self.stdout.write("🗑️  Clearing existing operational data...")

        WorkOrder.objects.all().delete()
        ContainerPosition.objects.all().delete()
        PreOrder.objects.all().delete()
        ContainerEntry.objects.all().delete()
        Container.objects.all().delete()  # Also clear container pool

        self.stdout.write(self.style.SUCCESS("  ✓ Operational data cleared\n"))

    def _load_foundation_data(self) -> Dict[str, Any]:
        """Load all foundation data from database"""
        foundation = {}

        # Load admin users
        foundation["system_admin"] = User.objects.filter(
            user_type="admin", username="system"
        ).first()
        foundation["controlroom_admin"] = User.objects.filter(
            user_type="admin", username="controlroom"
        ).first()

        # Fallback to any admin if specific ones don't exist
        if not foundation["system_admin"]:
            foundation["system_admin"] = User.objects.filter(user_type="admin", is_active=True).first()
        if not foundation["controlroom_admin"]:
            foundation["controlroom_admin"] = User.objects.filter(user_type="admin", is_active=True).first()

        self._log_item("Loaded admin users")

        # Load companies with size classification
        companies_size_map = {
            "uzrailways": "large",
            "tashkent-logistics": "large",
            "silk-road-transport": "medium",
            "navoi-freight": "medium",
            "bukhara-trans": "small",
            "samarkand-cargo": "small",
            "fergana-logistics": "small",
        }

        foundation["companies"] = list(Company.objects.filter(is_active=True))
        foundation["company_sizes"] = {}
        for company in foundation["companies"]:
            # Assign size based on slug, default to medium if unknown
            foundation["company_sizes"][company.id] = companies_size_map.get(company.slug, "medium")

        self._log_item(f"Loaded {len(foundation['companies'])} companies")

        # Load managers
        foundation["managers"] = list(User.objects.filter(user_type="manager", is_active=True))
        self._log_item(f"Loaded {len(foundation['managers'])} managers")

        # Load customers
        foundation["customers"] = list(User.objects.filter(user_type="customer", is_active=True))
        self._log_item(f"Loaded {len(foundation['customers'])} customers")

        # Load container owners
        foundation["container_owners"] = list(ContainerOwner.objects.all())
        foundation["owner_prefixes"] = {
            owner.id: owner.slug.upper()[:4].ljust(4, 'X')
            for owner in foundation["container_owners"]
        }
        self._log_item(f"Loaded {len(foundation['container_owners'])} container owners")

        # Load terminal vehicles
        foundation["vehicles"] = list(TerminalVehicle.objects.filter(is_active=True))
        self._log_item(f"Loaded {len(foundation['vehicles'])} terminal vehicles")

        return foundation

    def _generate_timeline_with_checkpoints(
        self,
        days: int,
        foundation: Dict[str, Any],
        container_pool: List[Container],
        state: Dict[str, Any],
    ):
        """Generate timeline with periodic checkpointing"""
        start_date = timezone.now() - timedelta(days=days)

        # If checkpointing disabled or dry run, use single transaction
        if self.checkpoint_every <= 0 or self.dry_run:
            with transaction.atomic():
                self._generate_timeline(days, foundation, container_pool, state, start_date, 0)
            return

        # Generate in chunks with checkpoints
        days_processed = 0
        while days_processed < days:
            chunk_size = min(self.checkpoint_every, days - days_processed)

            with transaction.atomic():
                self._generate_timeline(
                    chunk_size, foundation, container_pool, state, start_date, days_processed
                )

            days_processed += chunk_size
            if days_processed < days:
                self.stdout.write(
                    self.style.SUCCESS(f"  💾 Checkpoint: {days_processed}/{days} days saved")
                )

    def _create_container_pool(self, count: int) -> List[Container]:
        """Create pool of containers that will be reused"""
        containers = []

        # ISO types with correct size matching
        iso_types_40ft = ["42G1", "45G1", "45R1", "L5G1", "42R1", "42U1", "42P1", "42T1"]
        iso_types_20ft = ["22G1", "22R1", "22K2", "25G1", "22U1", "22P1", "22T1"]

        # 65% 40ft, 35% 20ft distribution (matches row allocation capacity)
        for i in range(count):
            is_40ft = random.random() < 0.65
            iso_types = iso_types_40ft if is_40ft else iso_types_20ft
            iso_type = random.choice(iso_types)

            # Generate realistic container number
            prefix = random.choice(["MSKU", "MSCU", "CMAU", "HLCU", "COSU"])
            number = f"{random.randint(1000000, 9999999):07d}"
            container_number = f"{prefix}{number}"

            container, _ = Container.objects.get_or_create(
                container_number=container_number,
                defaults={"iso_type": iso_type},
            )
            containers.append(container)

        self.stats["containers_created"] = len(containers)
        self._log_item(f"Created pool of {len(containers)} containers")
        return containers

    def _initialize_state(self, foundation: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize state tracking for type-segregated position allocation"""
        state = {
            "company_cursors": {},
            "active_entries": {},  # {container_id: entry_id}
            "exited_container_ids": set(),
            "occupancy_grid": {},  # {(zone, row, bay, tier, slot): entry_id}
            "overflow_cursors": {},  # {container_type: cursor}
            "stats_by_type": {},  # {container_type: {entries, exits, failed}}
        }

        # Initialize stats tracking by type
        for container_type in self.ROW_ALLOCATION.keys():
            state["stats_by_type"][container_type] = {
                "entries": 0,
                "exits": 0,
                "failed_placements": 0,
            }

        # Initialize overflow cursors (shared across all companies, one per type)
        for container_type, rows in self.ROW_ALLOCATION.items():
            state["overflow_cursors"][container_type] = {
                "rows": rows.copy(),
                "current_row_idx": 0,
                "current_bay": 1,
                "current_tier": 1,
                "positions_filled": 0,
                "positions_skipped": 0,
            }

        # Initialize company cursors (each company gets 4 cursors, one per type)
        for company in foundation["companies"]:
            state["company_cursors"][company.id] = {}
            for container_type, rows in self.ROW_ALLOCATION.items():
                state["company_cursors"][company.id][container_type] = {
                    "rows": rows.copy(),
                    "current_row_idx": 0,
                    "current_bay": 1,
                    "current_tier": 1,
                    "positions_filled": 0,
                    "positions_skipped": 0,
                }

        # Log allocation summary
        self._log_item(f"Terminal layout: Block A (10 rows × 10 bays × 4 tiers)")
        self._log_item(f"Row allocation by container type:")
        self.stdout.write(f"    • 40ft EMPTY: Rows {self.ROW_ALLOCATION[('40ft', 'EMPTY')]} (200 positions)")
        self.stdout.write(f"    • 40ft LADEN: Rows {self.ROW_ALLOCATION[('40ft', 'LADEN')]} (120 positions)")
        self.stdout.write(f"    • 20ft EMPTY: Rows {self.ROW_ALLOCATION[('20ft', 'EMPTY')]} (80 positions, 2 slots/bay)")
        self.stdout.write(f"    • 20ft LADEN: Rows {self.ROW_ALLOCATION[('20ft', 'LADEN')]} (80 positions, 2 slots/bay)")
        self.stdout.write(f"  Total capacity: ~480 containers")
        return state

    def _generate_timeline(
        self,
        days: int,
        foundation: Dict[str, Any],
        container_pool: List[Container],
        state: Dict[str, Any],
        start_date: datetime,
        days_offset: int = 0,
    ):
        """Generate chronological timeline of operations"""
        for day_offset in range(days):
            current_date = start_date + timedelta(days=days_offset + day_offset)

            # Volume: 10-30 containers per day
            daily_volume = random.randint(10, 30)

            # Transport mix: 70% truck, 30% train
            train_volume = int(daily_volume * 0.3)
            truck_volume = daily_volume - train_volume

            # Generate train batches
            train_entries = []
            while train_volume > 0:
                batch_size = min(random.randint(5, 15), train_volume)
                batch_entries = self._generate_train_batch(
                    batch_size, current_date, foundation, container_pool, state
                )
                train_entries.extend(batch_entries)
                train_volume -= batch_size

            # Generate truck entries
            truck_entries = []
            for _ in range(truck_volume):
                entry = self._generate_truck_entry(current_date, foundation, container_pool, state)
                if entry:
                    truck_entries.append(entry)

            # Process exits for this day
            self._process_exits(current_date, foundation, state)

            if self.verbosity >= 2 and day_offset % 10 == 0:
                total_day = days_offset + day_offset + 1
                self.stdout.write(
                    f"  Day {total_day}: {len(train_entries) + len(truck_entries)} entries created"
                )

        self._log_item(f"Completed {days} days of timeline generation (offset: {days_offset})")

    def _generate_train_batch(
        self,
        batch_size: int,
        current_date: datetime,
        foundation: Dict[str, Any],
        container_pool: List[Container],
        state: Dict[str, Any],
    ) -> List[ContainerEntry]:
        """Generate batch of train arrivals with same train number"""
        batch_entries = []
        train_number = f"T{random.randint(1000, 9999)}"
        base_time = current_date.replace(hour=random.randint(6, 20), minute=random.randint(0, 59))

        for i in range(batch_size):
            # Stagger arrival times by 5-15 minutes
            entry_time = base_time + timedelta(minutes=i * random.randint(5, 15))

            entry = self._create_container_entry(
                entry_time=entry_time,
                transport_type="TRAIN",
                train_number=train_number,
                foundation=foundation,
                container_pool=container_pool,
                state=state,
            )

            if entry:
                batch_entries.append(entry)

        return batch_entries

    def _generate_truck_entry(
        self,
        current_date: datetime,
        foundation: Dict[str, Any],
        container_pool: List[Container],
        state: Dict[str, Any],
    ) -> Optional[ContainerEntry]:
        """Generate single truck entry"""
        entry_time = current_date.replace(hour=random.randint(6, 22), minute=random.randint(0, 59))

        return self._create_container_entry(
            entry_time=entry_time,
            transport_type="TRUCK",
            train_number=None,
            foundation=foundation,
            container_pool=container_pool,
            state=state,
        )

    def _create_container_entry(
        self,
        entry_time: datetime,
        transport_type: str,
        train_number: Optional[str],
        foundation: Dict[str, Any],
        container_pool: List[Container],
        state: Dict[str, Any],
    ) -> Optional[ContainerEntry]:
        """Create container entry with complete workflow"""

        # Select or reuse container
        container = self._select_container(container_pool, state)
        if not container:
            return None

        # 60% empty, 40% laden (balanced for capacity)
        status = "EMPTY" if random.random() < 0.6 else "LADEN"

        # Select company and other details
        company = random.choice(foundation["companies"])
        recorded_by = random.choice(foundation["managers"])
        container_owner = random.choice(foundation["container_owners"])

        # Generate transport number
        if transport_type == "TRUCK":
            region = random.choice(["01", "10", "20", "30"])
            transport_number = f"{region}{random.choice('ABCD')}{random.randint(100, 999)}{random.choice('EF')}{random.choice('GH')}"
        else:
            transport_number = f"W{random.randint(100000, 999999)}"

        # 70% have pre-order
        if transport_type == "TRUCK" and random.random() < 0.7:
            preorder = self._create_preorder(
                transport_number, entry_time, foundation, random.choice(foundation["customers"])
            )
            if preorder:
                self.stats["preorders_created"] += 1

        # Create entry
        entry_data = {
            "container": container,
            "entry_time": entry_time,
            "status": status,
            "transport_type": transport_type,
            "transport_number": transport_number,
            "recorded_by": recorded_by,
            "company": company,
            "container_owner": container_owner,
            "client_name": random.choice([
                "Toshkent Savdo", "Navoiy Mining", "Buxoro Textile",
                "Samarqand Trade", "Farg'ona Agro"
            ]),
        }

        if train_number:
            entry_data["entry_train_number"] = train_number

        # Add cargo details for LADEN
        if status == "LADEN":
            entry_data["cargo_name"] = random.choice([
                "Paxta (Cotton)", "Meva-sabzavot", "Tekstil mahsulotlari",
                "Elektronika", "Qurilish materiallari"
            ])
            entry_data["cargo_weight"] = Decimal(str(round(random.uniform(5, 25), 2)))

        if not self.dry_run:
            entry = ContainerEntry.objects.create(**entry_data)
            self.stats["entries_created"] += 1

            # Create placement work order and position
            self._create_placement_work_order(entry, entry_time, foundation, state)

            return entry

        return None

    def _select_container(
        self, container_pool: List[Container], state: Dict[str, Any]
    ) -> Optional[Container]:
        """Select container from pool, allowing reuse after exit"""

        # 60% chance to reuse a container that has exited (realistic container cycling)
        if state["exited_container_ids"] and random.random() < 0.60:
            container_id = random.choice(list(state["exited_container_ids"]))
            container = Container.objects.get(id=container_id)

            # Prevent double-placement
            if container.id not in state["active_entries"]:
                return container

        # Otherwise use from pool (ensure not active)
        for _ in range(100):
            container = random.choice(container_pool)
            if container.id not in state["active_entries"]:
                return container

        return None  # All containers busy (shouldn't happen)

    def _create_preorder(
        self,
        plate_number: str,
        entry_time: datetime,
        foundation: Dict[str, Any],
        customer: User,
    ) -> Optional[PreOrder]:
        """Create pre-order before entry"""
        if self.dry_run:
            return None

        created_at = entry_time - timedelta(hours=random.randint(1, 24))

        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number=plate_number,
            operation_type=random.choice(["LOAD", "UNLOAD"]),
            status="PENDING",
            created_at=created_at,
        )

        return preorder

    def _create_placement_work_order(
        self,
        entry: ContainerEntry,
        entry_time: datetime,
        foundation: Dict[str, Any],
        state: Dict[str, Any],
    ):
        """Create PLACEMENT work order with guaranteed position allocation"""

        # Get container size using helper method (returns '20ft' or '40ft')
        iso_type = entry.container.iso_type
        size = self._get_container_size(iso_type)  # e.g., '40ft' or '20ft'
        is_40ft = size == '40ft'

        # Construct container type tuple for row allocation (size, status)
        # e.g., ('40ft', 'LADEN') or ('20ft', 'EMPTY')
        container_type = (size, entry.status)

        # Get position (guaranteed to succeed)
        position_coords = self._get_next_position_guaranteed(
            entry.company.id, container_type, is_40ft, state
        )
        if not position_coords:
            self._log_item(f"⚠️  Failed to allocate position for entry {entry.id}")
            return

        row, bay, tier, slot = position_coords

        # Determine status based on age (simplified: PENDING or COMPLETED)
        now = timezone.now()
        days_since_entry = (now.date() - entry_time.date()).days

        if days_since_entry <= 2:
            # Recent entries: some still pending
            status = random.choices(
                ["COMPLETED", "PENDING"],
                weights=[80, 20]
            )[0]
        else:
            # Historical: all completed
            status = "COMPLETED"

        # Create work order
        work_order = WorkOrder.objects.create(
            operation_type="PLACEMENT",
            container_entry=entry,
            status=status,
            priority="MEDIUM",
            assigned_to_vehicle=random.choice(foundation["vehicles"]),
            created_by=foundation["controlroom_admin"],
            target_zone="A",
            target_row=row,
            target_bay=bay,
            target_tier=tier,
            target_sub_slot=slot,
        )

        # Set realistic timestamps
        self._set_work_order_timestamps(work_order, entry_time, status)

        self.stats["work_orders_placement"] += 1

        # Create position with validation
        position = ContainerPosition(
            container_entry=entry,
            zone="A",
            row=row,
            bay=bay,
            tier=tier,
            sub_slot=slot,
            auto_assigned=True
        )

        try:
            # Validate model constraints (catches row>10, tier>4, etc.)
            position.full_clean()
            position.save()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"  ✗ Position validation failed for entry {entry.id}: {e}"
                )
            )
            # Clean up state - remove invalid position
            grid_key = ("A", row, bay, tier, slot)
            if grid_key in state["occupancy_grid"]:
                del state["occupancy_grid"][grid_key]
            if entry.container.id in state["active_entries"]:
                del state["active_entries"][entry.container.id]
            return

        # Update entry location
        entry.location = f"A-R{row:02d}-B{bay:02d}-T{tier}-{slot}"
        entry.save(update_fields=["location"])

        # Mark in state
        state["occupancy_grid"][("A", row, bay, tier, slot)] = entry.id
        state["active_entries"][entry.container.id] = entry.id
        self.stats["positions_created"] += 1

    def _set_work_order_timestamps(self, work_order: WorkOrder, entry_time: datetime, status: str):
        """Set realistic workflow timestamps (simplified: PENDING or COMPLETED)"""
        created_at = entry_time + timedelta(minutes=random.randint(5, 10))

        if status == "COMPLETED":
            completed_at = created_at + timedelta(minutes=random.randint(15, 30))
            WorkOrder.objects.filter(id=work_order.id).update(
                created_at=created_at,
                completed_at=completed_at,
            )
        else:  # PENDING
            WorkOrder.objects.filter(id=work_order.id).update(
                created_at=created_at,
            )

    def _get_next_position_guaranteed(
        self, company_id: int, container_type: Tuple[str, str], is_40ft: bool, state: Dict[str, Any]
    ) -> Optional[Tuple[int, int, int, str]]:
        """
        Get next position for container type with guaranteed success.
        Fallback chain: company cursor (for type) → overflow cursor (for type)

        Args:
            company_id: ID of company placing container
            container_type: Tuple of (size, status) e.g., ('40ft', 'LADEN')
            is_40ft: Whether container is 40ft (determines slot logic)
            state: State dictionary with cursors and occupancy grid

        Returns:
            Tuple of (row, bay, tier, slot) or None if terminal at capacity for this type
        """
        # Try company-specific cursor for this container type
        position = self._get_position_from_cursor(
            state["company_cursors"][company_id][container_type], is_40ft, state
        )
        if position:
            return position

        # Try overflow cursor for this container type
        position = self._get_position_from_cursor(
            state["overflow_cursors"][container_type], is_40ft, state
        )
        if position:
            return position

        # Terminal capacity reached for this container type
        size, status = container_type
        if self.verbosity >= 2:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠️  Terminal capacity reached for {size} {status} containers. "
                    f"Cannot place - rows {self.ROW_ALLOCATION[container_type]} are full."
                )
            )
        return None  # Fail placement gracefully

    def _get_container_size(self, iso_type: str) -> str:
        """
        Extract container size from ISO 6346 type code.

        ISO type format: First character indicates length
        - '2' = 20ft containers (22G1, 25G1, 22R1, 22K2, etc.)
        - '4' = 40ft containers (42G1, 42R1, 42U1, 42P1, etc.)
        - 'L' = 45ft containers (L5G1, L5R1, etc.) → treated as 40ft for bay purposes

        Args:
            iso_type: ISO container type code (e.g., '22G1', '42G1', 'L5G1')

        Returns:
            '20ft' or '40ft'

        Raises:
            ValueError: If ISO type is unrecognized
        """
        first_char = iso_type[0].upper()
        if first_char == '2':
            return '20ft'
        elif first_char in ('4', 'L'):  # 45ft uses 40ft bay space
            return '40ft'
        else:
            raise ValueError(f"Unknown ISO type: {iso_type}")

    def _has_support_below_in_state(
        self, zone: str, row: int, bay: int, tier: int, slot: str, state: Dict[str, Any]
    ) -> bool:
        """
        Check if position has container below using occupancy_grid.

        Args:
            zone: Terminal zone (A-E)
            row: Row number (1-10)
            bay: Bay number (1-10)
            tier: Tier level (1-4)
            slot: Sub-slot (A or B)
            state: State dictionary with occupancy_grid

        Returns:
            True if tier 1 (ground level) or container exists at tier-1
        """
        if tier == 1:
            return True  # Ground level always has support

        below_key = (zone, row, bay, tier - 1, slot)
        return below_key in state["occupancy_grid"]

    def _get_position_from_cursor(
        self, cursor: Dict[str, Any], is_40ft: bool, state: Dict[str, Any]
    ) -> Optional[Tuple[int, int, int, str]]:
        """
        Find available position in assigned rows.
        Scans ALL positions in the rows (not just cursor position) to handle vacated spots.
        Uses ground-up stacking: tier 1 first, then 2, 3, 4.
        """
        rows = cursor["rows"]

        # Scan all positions in assigned rows (ground-up stacking)
        for row in rows:
            for bay in range(1, 11):  # Bays 1-10
                for tier in range(1, 5):  # Tiers 1-4 (ground up)
                    position_key_a = ("A", row, bay, tier, "A")
                    position_key_b = ("A", row, bay, tier, "B")

                    # Try to place 40ft container
                    if is_40ft:
                        can_place = position_key_a not in state["occupancy_grid"]

                        if can_place and tier > 1:
                            # Check vertical support
                            can_place = self._has_support_below_in_state("A", row, bay, tier, "A", state)

                            # 40ft needs full bay support (both A and B below, or both empty)
                            if can_place:
                                below_a = ("A", row, bay, tier - 1, "A")
                                below_b = ("A", row, bay, tier - 1, "B")
                                a_exists = below_a in state["occupancy_grid"]
                                b_exists = below_b in state["occupancy_grid"]
                                if a_exists != b_exists:
                                    can_place = False

                        if can_place:
                            cursor["positions_filled"] += 1
                            return (row, bay, tier, "A")

                    # Try to place 20ft container
                    if not is_40ft:
                        # Check slot A first
                        can_place_a = position_key_a not in state["occupancy_grid"]
                        if can_place_a and tier > 1:
                            can_place_a = self._has_support_below_in_state("A", row, bay, tier, "A", state)

                        if can_place_a:
                            cursor["positions_filled"] += 1
                            return (row, bay, tier, "A")

                        # Check slot B
                        can_place_b = position_key_b not in state["occupancy_grid"]
                        if can_place_b and tier > 1:
                            can_place_b = self._has_support_below_in_state("A", row, bay, tier, "B", state)

                        if can_place_b:
                            cursor["positions_filled"] += 1
                            return (row, bay, tier, "B")

        return None  # No space available in assigned rows

    def _advance_cursor(self, cursor: Dict[str, Any]):
        """
        Move cursor to next position (tier-major, bay-major, row-major).

        Stacking order: Fill tiers 1-4 of each bay before moving to next bay.
        This ensures ground-first physics (no floating containers).
        """
        cursor["current_tier"] += 1  # Stack vertically first

        if cursor["current_tier"] > 4:
            # All 4 tiers of this bay done, move to next bay
            cursor["current_bay"] += 1
            cursor["current_tier"] = 1

            if cursor["current_bay"] > 10:
                # All 10 bays done, move to next row
                cursor["current_row_idx"] += 1
                cursor["current_bay"] = 1
                cursor["current_tier"] = 1

    def _can_exit(self, entry: ContainerEntry, state: Dict[str, Any]) -> bool:
        """Check if container can exit (no containers stacked above)"""
        try:
            position = entry.position
        except ContainerPosition.DoesNotExist:
            return False

        if position.tier == 4:
            return True  # Top tier can always exit

        # Check for containers above
        for tier_above in range(position.tier + 1, 5):
            above_key = ("A", position.row, position.bay, tier_above, position.sub_slot)
            if above_key in state["occupancy_grid"]:
                return False
        return True

    def _process_exits(self, current_date: datetime, foundation: Dict[str, Any], state: Dict[str, Any]):
        """Process container exits with RETRIEVAL work orders (only containers that CAN exit)"""

        if self.dry_run:
            return

        # Build list of candidates that CAN exit (no stack above)
        exit_candidates = []
        for container_id, entry_id in list(state["active_entries"].items()):
            entry = ContainerEntry.objects.get(id=entry_id)

            # Skip if container can't physically exit (has stack above)
            if not self._can_exit(entry, state):
                continue

            days_on_terminal = (current_date.date() - entry.entry_time.date()).days

            # Determine exit probability based on dwell time
            # Low exit rates to build up terminal density to ~80%
            exit_probability = 0.0
            if 1 <= days_on_terminal <= 7:
                exit_probability = 0.03  # 3% - most containers stay at least a week
            elif 8 <= days_on_terminal <= 14:
                exit_probability = 0.08  # 8% - two week stay
            elif 15 <= days_on_terminal <= 30:
                exit_probability = 0.15  # 15% - month-long stay
            elif days_on_terminal > 30:
                exit_probability = 0.30  # 30% - eventually must exit

            if exit_probability > 0 and random.random() < exit_probability:
                try:
                    position = entry.position
                    tier = position.tier
                except ContainerPosition.DoesNotExist:
                    continue
                exit_candidates.append((tier, entry))

        # Sort by tier descending (tier 4 first, tier 1 last) - LIFO strategy
        exit_candidates.sort(key=lambda x: -x[0])

        # Process exits in LIFO order
        for tier, entry in exit_candidates:
            exit_time = current_date.replace(
                hour=random.randint(8, 20), minute=random.randint(0, 59)
            )
            self._process_exit_with_retrieval(entry, exit_time, foundation, state)

    def _process_exit_with_retrieval(
        self,
        entry: ContainerEntry,
        exit_date: datetime,
        foundation: Dict[str, Any],
        state: Dict[str, Any],
    ):
        """Process exit with RETRIEVAL work order"""

        # Get position (always exists, 100% placement success)
        try:
            position = entry.position
        except ContainerPosition.DoesNotExist:
            # Shouldn't happen, but handle gracefully
            self._log_item(f"⚠️  Entry {entry.id} has no position, skipping retrieval work order")
            return

        # Create retrieval work order timeline (simplified)
        wo_created = exit_date - timedelta(hours=random.randint(2, 6))
        wo_completed = exit_date  # Truck departure = completion

        # Create RETRIEVAL work order
        work_order = WorkOrder.objects.create(
            operation_type="RETRIEVAL",
            container_entry=entry,
            status="COMPLETED",  # All retrievals completed
            priority="MEDIUM",
            assigned_to_vehicle=random.choice(foundation["vehicles"]),
            created_by=foundation["controlroom_admin"],
            target_zone=position.zone,
            target_row=position.row,
            target_bay=position.bay,
            target_tier=position.tier,
            target_sub_slot=position.sub_slot,
        )

        # Set timestamps (simplified: created_at and completed_at only)
        WorkOrder.objects.filter(id=work_order.id).update(
            created_at=wo_created,
            completed_at=wo_completed,
        )

        self.stats["work_orders_retrieval"] += 1

        # Update entry with exit data
        entry.exit_date = exit_date
        entry.exit_transport_type = random.choice(["TRUCK", "TRAIN"])

        if entry.exit_transport_type == "TRUCK":
            region = random.choice(["01", "10", "20", "30"])
            entry.exit_transport_number = f"{region}{random.choice('ABCD')}{random.randint(100, 999)}{random.choice('EF')}{random.choice('GH')}"
        else:
            entry.exit_transport_number = f"W{random.randint(100000, 999999)}"
            entry.exit_train_number = f"T{random.randint(1000, 9999)}"

        entry.destination_station = random.choice([
            "Toshkent-Tovarniy", "Chukursay", "Sergeli", "Bekabad"
        ])
        entry.location = ""
        entry.save()

        # Note: Stack check already done in _can_exit() before calling this method
        # Delete position
        grid_key = ("A", position.row, position.bay, position.tier, position.sub_slot)
        if grid_key in state["occupancy_grid"]:
            del state["occupancy_grid"][grid_key]

        position.delete()

        # Mark container available for reuse
        if entry.container.id in state["active_entries"]:
            del state["active_entries"][entry.container.id]
        state["exited_container_ids"].add(entry.container.id)

        self.stats["exits_processed"] += 1

    def _get_or_create_user(
        self, username: str, user_type: str, first_name: str, last_name: str
    ) -> User:
        """Get or create user"""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "user_type": user_type,
                "is_staff": user_type == "admin",
                "is_active": True,
            },
        )

        if created:
            user.set_password(f"{user_type}123")
            user.save()

        return user

    def _log_phase(self, message: str):
        """Log phase header"""
        self.stdout.write(self.style.NOTICE(f"\n{message}"))

    def _log_item(self, message: str):
        """Log individual item"""
        if self.verbosity >= 1:
            self.stdout.write(f"  ✓ {message}")

    def _print_statistics(self):
        """Print final generation statistics"""
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("📊 GENERATION COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"\n  Containers created: {self.stats['containers_created']}")
        self.stdout.write(f"  Container entries: {self.stats['entries_created']}")
        self.stdout.write(f"  Pre-orders created: {self.stats['preorders_created']}")
        self.stdout.write(f"  Work orders (PLACEMENT): {self.stats['work_orders_placement']}")
        self.stdout.write(f"  Work orders (RETRIEVAL): {self.stats['work_orders_retrieval']}")
        self.stdout.write(
            f"  Work orders (TOTAL): {self.stats['work_orders_placement'] + self.stats['work_orders_retrieval']}"
        )
        self.stdout.write(f"  Positions created: {self.stats['positions_created']}")
        self.stdout.write(f"  Exits processed: {self.stats['exits_processed']}")
        self.stdout.write(
            f"\n  Containers on terminal: {self.stats['entries_created'] - self.stats['exits_processed']}"
        )
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70 + "\n"))

    def _verify_placements(self):
        """Verify placement integrity after generation"""
        from django.db.models import Max

        # Build position lookup dictionary
        positions = ContainerPosition.objects.all()
        position_dict = {
            (p.zone, p.row, p.bay, p.tier, p.sub_slot): p
            for p in positions
        }

        # Check 1: Floating containers (tier > 1 with no support)
        floating_count = 0
        for (zone, row, bay, tier, slot), pos in position_dict.items():
            if tier > 1:
                below_key = (zone, row, bay, tier - 1, slot)
                if below_key not in position_dict:
                    floating_count += 1
                    if self.verbosity >= 2:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️  Floating container at {zone}-R{row:02d}-B{bay:02d}-T{tier}-{slot}"
                            )
                        )

        # Check 2: Boundary violations
        boundary_violations = ContainerPosition.objects.filter(row__gt=10).count()

        # Check 3: Density calculation
        total_capacity = 10 * 10 * 4  # 10 rows × 10 bays × 4 tiers (ignoring slots)
        actual_positions = positions.count()
        density = (actual_positions / total_capacity * 100) if total_capacity > 0 else 0

        # Check 4: Maximum row number
        max_row = ContainerPosition.objects.aggregate(Max('row'))['row__max'] or 0

        # Report verification results
        self.stdout.write(self.style.SUCCESS("\n📋 VERIFICATION RESULTS"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        if floating_count == 0:
            self.stdout.write(self.style.SUCCESS(f"  ✓ No floating containers (target: 0)"))
        else:
            self.stdout.write(self.style.ERROR(f"  ✗ Floating containers: {floating_count} (target: 0)"))

        if boundary_violations == 0:
            self.stdout.write(self.style.SUCCESS(f"  ✓ All containers within boundaries (rows 1-10)"))
        else:
            self.stdout.write(self.style.ERROR(f"  ✗ Boundary violations: {boundary_violations} (target: 0)"))

        if max_row <= 10:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Maximum row: {max_row} (≤10)"))
        else:
            self.stdout.write(self.style.ERROR(f"  ✗ Maximum row: {max_row} (target: ≤10)"))

        self.stdout.write(f"  ℹ️  Terminal density: {density:.1f}% (target: ~80%)")
        self.stdout.write(f"  ℹ️  Total positions: {actual_positions}")
        self.stdout.write(self.style.SUCCESS("=" * 70 + "\n"))
