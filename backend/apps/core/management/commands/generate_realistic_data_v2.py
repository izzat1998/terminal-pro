"""
Generate 90 days of realistic data with tight company clustering (v2).

Key improvements over v1:
- Sequential position allocation (tight company clusters)
- 100% placement success (no failed work orders)
- Complete lifecycle with PLACEMENT + RETRIEVAL work orders
- 80% density target (operational gaps)
- Proper 20ft/40ft slot logic and tier stacking physics

Usage:
    python manage.py generate_realistic_data_v2              # Generate 90 days
    python manage.py generate_realistic_data_v2 --days 30    # Custom days
    python manage.py generate_realistic_data_v2 --clear      # Clear existing data first
    python manage.py generate_realistic_data_v2 --dry-run    # Simulate without saving
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
    help = "Generate 90 days of realistic data with tight company clustering (v2)"

    def add_arguments(self, parser):
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

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN MODE - No data will be saved\n"))

        self.stdout.write(
            self.style.NOTICE(f"🚀 Starting realistic data generation (v2) for {days} days...\n")
        )

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
            with transaction.atomic():
                # Phase 1: Foundation data
                self._log_phase("Phase 1: Creating foundation data")
                foundation = self._create_foundation_data()

                # Phase 2: Container pool
                self._log_phase("Phase 2: Creating container pool")
                container_pool = self._create_container_pool(100)

                # Phase 3: Space allocation
                self._log_phase("Phase 3: Initializing space allocation")
                state = self._initialize_state(foundation)

                # Phase 4: Chronological generation
                self._log_phase(f"Phase 4: Generating {days} days of operations")
                self._generate_timeline(days, foundation, container_pool, state)

                if self.dry_run:
                    self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - Rolling back transaction\n"))
                    raise Exception("Dry run - transaction rolled back")

            # Final statistics
            self._print_statistics()

        except Exception as e:
            if not self.dry_run or str(e) != "Dry run - transaction rolled back":
                self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}\n"))
                raise

    def _clear_operational_data(self):
        """Clear operational data while preserving foundation data"""
        self.stdout.write("🗑️  Clearing existing operational data...")

        WorkOrder.objects.all().delete()
        ContainerPosition.objects.all().delete()
        PreOrder.objects.all().delete()
        ContainerEntry.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("  ✓ Operational data cleared\n"))

    def _create_foundation_data(self) -> Dict[str, Any]:
        """Create all foundation data needed for operations"""
        foundation = {}

        # 1. Create admin users
        foundation["system_admin"] = self._get_or_create_user(
            username="system",
            user_type="admin",
            first_name="System",
            last_name="Administrator",
        )
        foundation["controlroom_admin"] = self._get_or_create_user(
            username="controlroom",
            user_type="admin",
            first_name="Control",
            last_name="Room",
        )

        # 2. Create companies with size classification
        companies_data = [
            {"name": "O'zbekiston Temir Yo'llari", "slug": "uzrailways", "size": "large"},
            {"name": "Toshkent Logistika", "slug": "tashkent-logistics", "size": "large"},
            {"name": "Ipak Yo'li Transport", "slug": "silk-road-transport", "size": "medium"},
            {"name": "Navoiy Yuk Tashish", "slug": "navoi-freight", "size": "medium"},
            {"name": "Buxoro Trans", "slug": "bukhara-trans", "size": "small"},
            {"name": "Samarqand Cargo", "slug": "samarkand-cargo", "size": "small"},
            {"name": "Farg'ona Logistics", "slug": "fergana-logistics", "size": "small"},
        ]

        foundation["companies"] = []
        foundation["company_sizes"] = {}
        for data in companies_data:
            company, _ = Company.objects.get_or_create(
                slug=data["slug"],
                defaults={"name": data["name"], "is_active": True},
            )
            foundation["companies"].append(company)
            foundation["company_sizes"][company.id] = data["size"]

        self._log_item(f"Created {len(foundation['companies'])} companies")

        # 3. Create managers
        managers_data = [
            {"first_name": "Aziz", "last_name": "Karimov", "phone": "+998901234567"},
            {"first_name": "Bobur", "last_name": "Toshmatov", "phone": "+998902345678"},
            {"first_name": "Sardor", "last_name": "Normatov", "phone": "+998903456789"},
            {"first_name": "Dilshod", "last_name": "Saidov", "phone": "+998904567890"},
        ]

        foundation["managers"] = []
        for data in managers_data:
            user = self._get_or_create_user(
                username=f"{data['first_name'].lower()}_manager",
                user_type="manager",
                first_name=data["first_name"],
                last_name=data["last_name"],
            )

            profile, _ = ManagerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": data["phone"],
                    "telegram_user_id": random.randint(100000000, 999999999),
                    "bot_access": True,
                    "gate_access": True,
                    "language": "ru",
                },
            )
            foundation["managers"].append(user)

        self._log_item(f"Created {len(foundation['managers'])} managers")

        # 4. Create customers
        customers_data = [
            {"first_name": "Jamshid", "last_name": "Rahimov", "phone": "+998911234567"},
            {"first_name": "Kamol", "last_name": "Umarov", "phone": "+998912345678"},
            {"first_name": "Laziz", "last_name": "Tursunov", "phone": "+998913456789"},
        ]

        foundation["customers"] = []
        for i, data in enumerate(customers_data):
            user = self._get_or_create_user(
                username=f"{data['first_name'].lower()}_customer",
                user_type="customer",
                first_name=data["first_name"],
                last_name=data["last_name"],
            )

            company = foundation["companies"][i % len(foundation["companies"])]
            profile, _ = CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": data["phone"],
                    "telegram_user_id": random.randint(100000000, 999999999),
                    "bot_access": True,
                    "language": "ru",
                    "company": company,
                },
            )
            foundation["customers"].append(user)

        self._log_item(f"Created {len(foundation['customers'])} customers")

        # 5. Create container owners
        owners_data = [
            {"name": "Maersk Line", "slug": "maersk", "prefix": "MSKU"},
            {"name": "MSC - Mediterranean Shipping", "slug": "msc", "prefix": "MSCU"},
            {"name": "CMA CGM", "slug": "cma-cgm", "prefix": "CMAU"},
            {"name": "Hapag-Lloyd", "slug": "hapag-lloyd", "prefix": "HLCU"},
            {"name": "COSCO Shipping", "slug": "cosco", "prefix": "COSU"},
        ]

        foundation["container_owners"] = []
        foundation["owner_prefixes"] = {}
        for data in owners_data:
            owner, _ = ContainerOwner.objects.get_or_create(
                slug=data["slug"],
                defaults={"name": data["name"]},
            )
            foundation["container_owners"].append(owner)
            foundation["owner_prefixes"][owner.id] = data["prefix"]

        self._log_item(f"Created {len(foundation['container_owners'])} container owners")

        # 6. Create terminal vehicles
        vehicles_data = [
            {"name": "RS-01", "operator_idx": 0},
            {"name": "RS-02", "operator_idx": 1},
            {"name": "RS-03", "operator_idx": 2},
        ]

        foundation["vehicles"] = []
        for data in vehicles_data:
            operator = foundation["managers"][data["operator_idx"]]
            vehicle, _ = TerminalVehicle.objects.get_or_create(
                name=data["name"],
                defaults={
                    "vehicle_type": "REACH_STACKER",
                    "is_active": True,
                    "operator": operator,
                },
            )
            foundation["vehicles"].append(vehicle)

        self._log_item(f"Created {len(foundation['vehicles'])} terminal vehicles")

        # 7. Create tariffs
        self._create_tariffs(foundation["companies"])

        return foundation

    def _create_tariffs(self, companies: List[Company]):
        """Create tariffs covering the full period"""
        start_date = timezone.now().date() - timedelta(days=100)

        system_admin = User.objects.filter(user_type="admin", username="system").first()
        if not system_admin:
            system_admin = User.objects.filter(user_type="admin").first()

        # General tariff
        general_tariff, created = Tariff.objects.get_or_create(
            company=None,
            effective_from=start_date,
            defaults={
                "created_by": system_admin,
                "notes": "General tariff for all companies",
            },
        )

        if created:
            rates_data = [
                {"size": "20", "status": "EMPTY", "usd": "4.00", "uzs": "50000.00", "free": 3},
                {"size": "20", "status": "LADEN", "usd": "5.00", "uzs": "62500.00", "free": 3},
                {"size": "40", "status": "EMPTY", "usd": "6.00", "uzs": "75000.00", "free": 3},
                {"size": "40", "status": "LADEN", "usd": "8.00", "uzs": "100000.00", "free": 3},
            ]

            for rate_data in rates_data:
                TariffRate.objects.create(
                    tariff=general_tariff,
                    container_size=rate_data["size"],
                    container_status=rate_data["status"],
                    daily_rate_usd=Decimal(rate_data["usd"]),
                    daily_rate_uzs=Decimal(rate_data["uzs"]),
                    free_days=rate_data["free"],
                )

        # Company-specific tariffs (better rates for large companies)
        for company in companies[:2]:
            company_tariff, created = Tariff.objects.get_or_create(
                company=company,
                effective_from=start_date,
                defaults={
                    "created_by": system_admin,
                    "notes": f"Special tariff for {company.name}",
                },
            )

            if created:
                rates_data = [
                    {"size": "20", "status": "EMPTY", "usd": "3.00", "uzs": "37500.00", "free": 5},
                    {"size": "20", "status": "LADEN", "usd": "4.00", "uzs": "50000.00", "free": 5},
                    {"size": "40", "status": "EMPTY", "usd": "5.00", "uzs": "62500.00", "free": 5},
                    {"size": "40", "status": "LADEN", "usd": "6.50", "uzs": "81250.00", "free": 5},
                ]

                for rate_data in rates_data:
                    TariffRate.objects.create(
                        tariff=company_tariff,
                        container_size=rate_data["size"],
                        container_status=rate_data["status"],
                        daily_rate_usd=Decimal(rate_data["usd"]),
                        daily_rate_uzs=Decimal(rate_data["uzs"]),
                        free_days=rate_data["free"],
                    )

        self._log_item("Created tariffs with rates covering full period")

    def _create_container_pool(self, count: int) -> List[Container]:
        """Create pool of containers that will be reused"""
        containers = []

        # ISO types with correct size matching
        iso_types_40ft = ["42G1", "45G1", "45R1", "L5G1", "42R1", "42U1", "42P1", "42T1"]
        iso_types_20ft = ["22G1", "22R1", "22K2", "25G1", "22U1", "22P1", "22T1"]

        # 70% 40ft, 30% 20ft distribution
        for i in range(count):
            is_40ft = random.random() < 0.7
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
        """Initialize state tracking for sequential position allocation"""
        state = {
            "company_cursors": {},
            "active_entries": {},  # {container_id: entry_id}
            "exited_container_ids": set(),
            "occupancy_grid": {},  # {(zone, row, bay, tier, slot): entry_id}
            "overflow_cursor": None,
        }

        # Assign rows to companies (sequential allocation)
        row_assignments = {
            "large": 4,   # rows per large company
            "medium": 2,  # rows per medium company
            "small": 1,   # rows per small company
        }

        current_row = 1
        for company in foundation["companies"]:
            size = foundation["company_sizes"][company.id]
            num_rows = row_assignments[size]

            # Assign rows to this company
            company_rows = list(range(current_row, current_row + num_rows))
            current_row += num_rows

            # Initialize cursor for this company
            state["company_cursors"][company.id] = {
                "rows": company_rows,
                "current_row_idx": 0,
                "current_bay": 1,
                "current_tier": 1,
                "bay_occupancy": {},  # {bay_num: "FULL" | "SLOT_A_USED" | "EMPTY"}
                "positions_filled": 0,
                "positions_skipped": 0,
            }

        # Initialize overflow cursor (rows 16-20)
        state["overflow_cursor"] = {
            "rows": list(range(16, 21)),
            "current_row_idx": 0,
            "current_bay": 1,
            "current_tier": 1,
            "bay_occupancy": {},
            "positions_filled": 0,
            "positions_skipped": 0,
        }

        self._log_item(f"Initialized space allocation: rows 1-{current_row-1} assigned, overflow: 16-20")
        return state

    def _generate_timeline(
        self,
        days: int,
        foundation: Dict[str, Any],
        container_pool: List[Container],
        state: Dict[str, Any],
    ):
        """Generate chronological timeline of operations"""
        start_date = timezone.now() - timedelta(days=days)

        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)

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
                self.stdout.write(
                    f"  Day {day_offset + 1}/{days}: {len(train_entries) + len(truck_entries)} entries created"
                )

        self._log_item(f"Completed {days} days of timeline generation")

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

        # 70% empty, 30% laden
        status = "EMPTY" if random.random() < 0.7 else "LADEN"

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

        # 25% chance to reuse a container that has exited
        if state["exited_container_ids"] and random.random() < 0.25:
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

        # Get container size
        iso_type = entry.container.iso_type
        size = "40" if iso_type[0] in ["4", "L"] else "20"

        # Get position (guaranteed to succeed)
        position_coords = self._get_next_position_guaranteed(entry.company.id, size, state)
        if not position_coords:
            self._log_item(f"⚠️  Failed to allocate position for entry {entry.id}")
            return

        row, bay, tier, slot = position_coords

        # Determine status based on age
        now = timezone.now()
        days_since_entry = (now.date() - entry_time.date()).days

        if days_since_entry <= 2:
            # Recent entries: show active workflow
            status = random.choices(
                ["VERIFIED", "IN_PROGRESS", "ACCEPTED"],
                weights=[70, 20, 10]
            )[0]
        else:
            # Historical: all completed
            status = "VERIFIED"

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
            sla_deadline=entry_time + timedelta(hours=1),
        )

        # Set realistic timestamps
        self._set_work_order_timestamps(work_order, entry_time, status)

        self.stats["work_orders_placement"] += 1

        # Create position (always, since 100% success)
        ContainerPosition.objects.create(
            container_entry=entry,
            zone="A",
            row=row,
            bay=bay,
            tier=tier,
            sub_slot=slot,
            auto_assigned=True
        )

        # Update entry location
        entry.location = f"A-R{row:02d}-B{bay:02d}-T{tier}-{slot}"
        entry.save(update_fields=["location"])

        # Mark in state
        state["occupancy_grid"][("A", row, bay, tier, slot)] = entry.id
        state["active_entries"][entry.container.id] = entry.id
        self.stats["positions_created"] += 1

    def _set_work_order_timestamps(self, work_order: WorkOrder, entry_time: datetime, status: str):
        """Set realistic workflow timestamps"""
        created_at = entry_time + timedelta(minutes=random.randint(5, 10))
        assigned_at = created_at + timedelta(minutes=random.randint(2, 5))
        accepted_at = assigned_at + timedelta(minutes=random.randint(1, 3))
        started_at = accepted_at + timedelta(minutes=random.randint(2, 5))
        completed_at = started_at + timedelta(minutes=random.randint(10, 20))
        verified_at = completed_at + timedelta(minutes=random.randint(2, 5))

        if status == "VERIFIED":
            WorkOrder.objects.filter(id=work_order.id).update(
                created_at=created_at,
                assigned_at=assigned_at,
                accepted_at=accepted_at,
                started_at=started_at,
                completed_at=completed_at,
                verified_at=verified_at,
            )
        elif status == "IN_PROGRESS":
            WorkOrder.objects.filter(id=work_order.id).update(
                created_at=created_at,
                assigned_at=assigned_at,
                accepted_at=accepted_at,
                started_at=started_at,
            )
        elif status == "ACCEPTED":
            WorkOrder.objects.filter(id=work_order.id).update(
                created_at=created_at,
                assigned_at=assigned_at,
                accepted_at=accepted_at,
            )

    def _get_next_position_guaranteed(
        self, company_id: int, size: str, state: Dict[str, Any]
    ) -> Optional[Tuple[int, int, int, str]]:
        """
        Get next position with guaranteed success.
        Fallback chain: company zone → overflow → dynamic expansion
        """
        is_40ft = (size == "40")

        # Try company zone
        position = self._get_position_from_cursor(
            state["company_cursors"][company_id], is_40ft, state
        )
        if position:
            return position

        # Try overflow
        position = self._get_position_from_cursor(
            state["overflow_cursor"], is_40ft, state
        )
        if position:
            return position

        # Dynamically expand overflow
        new_row = max(state["overflow_cursor"]["rows"]) + 1
        state["overflow_cursor"]["rows"].append(new_row)
        state["overflow_cursor"]["current_row_idx"] = len(state["overflow_cursor"]["rows"]) - 1
        state["overflow_cursor"]["current_bay"] = 1
        state["overflow_cursor"]["current_tier"] = 1
        state["overflow_cursor"]["bay_occupancy"] = {}

        return self._get_position_from_cursor(state["overflow_cursor"], is_40ft, state)

    def _get_position_from_cursor(
        self, cursor: Dict[str, Any], is_40ft: bool, state: Dict[str, Any]
    ) -> Optional[Tuple[int, int, int, str]]:
        """Try to find position using cursor (sequential allocation)"""

        attempts = 0
        max_attempts = 200

        while cursor["current_row_idx"] < len(cursor["rows"]) and attempts < max_attempts:
            attempts += 1
            row = cursor["rows"][cursor["current_row_idx"]]
            bay = cursor["current_bay"]
            tier = cursor["current_tier"]

            # 80% density: 20% chance to skip this position
            if random.random() < 0.2:
                cursor["positions_skipped"] += 1
                self._advance_cursor(cursor)
                continue

            # Check bay occupancy
            bay_status = cursor["bay_occupancy"].get(bay, "EMPTY")

            # Try to place 40ft container
            if is_40ft and bay_status == "EMPTY":
                cursor["bay_occupancy"][bay] = "FULL"
                cursor["positions_filled"] += 1
                position = (row, bay, tier, "A")
                self._advance_cursor(cursor)
                return position

            # Try to place 20ft container
            if not is_40ft:
                if bay_status == "EMPTY":
                    # Use slot A
                    cursor["bay_occupancy"][bay] = "SLOT_A_USED"
                    cursor["positions_filled"] += 1
                    position = (row, bay, tier, "A")
                    self._advance_cursor(cursor)
                    return position
                elif bay_status == "SLOT_A_USED":
                    # Use slot B
                    cursor["bay_occupancy"][bay] = "FULL"
                    cursor["positions_filled"] += 1
                    position = (row, bay, tier, "B")
                    self._advance_cursor(cursor)
                    return position

            # Position not suitable, advance cursor
            self._advance_cursor(cursor)

        return None

    def _advance_cursor(self, cursor: Dict[str, Any]):
        """Move cursor to next position (bay-major, tier 1 first)"""
        cursor["current_bay"] += 1

        if cursor["current_bay"] > 10:
            if cursor["current_tier"] == 1:
                # Tier 1 done, move to tier 2
                cursor["current_tier"] = 2
                cursor["current_bay"] = 1
                # DON'T reset bay_occupancy for tier 2
                # (we need to track which bays are occupied on tier 1)
            else:
                # Tier 2 done, move to next row
                cursor["current_row_idx"] += 1
                cursor["current_tier"] = 1
                cursor["current_bay"] = 1
                cursor["bay_occupancy"] = {}  # Reset for new row

    def _process_exits(self, current_date: datetime, foundation: Dict[str, Any], state: Dict[str, Any]):
        """Process container exits with RETRIEVAL work orders"""

        # Get entries that could exit today
        for container_id, entry_id in list(state["active_entries"].items()):
            if self.dry_run:
                continue

            entry = ContainerEntry.objects.get(id=entry_id)
            days_on_terminal = (current_date.date() - entry.entry_time.date()).days

            # Determine if should exit (realistic dwell time distribution)
            should_exit = False
            if 1 <= days_on_terminal <= 3 and random.random() < 0.35:
                should_exit = True  # 35% for quick exit
            elif 4 <= days_on_terminal <= 10 and random.random() < 0.20:
                should_exit = True  # 20% for medium stay
            elif days_on_terminal >= 11 and random.random() < 0.30:
                should_exit = True  # 30% for long stay

            if should_exit:
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

        # Create retrieval work order timeline
        wo_created = exit_date - timedelta(hours=random.randint(2, 6))
        wo_assigned = wo_created + timedelta(minutes=random.randint(5, 15))
        wo_accepted = wo_assigned + timedelta(minutes=random.randint(1, 5))
        wo_started = wo_accepted + timedelta(minutes=random.randint(5, 15))
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
            sla_deadline=wo_created + timedelta(hours=1),
        )

        # Set timestamps
        WorkOrder.objects.filter(id=work_order.id).update(
            created_at=wo_created,
            assigned_at=wo_assigned,
            accepted_at=wo_accepted,
            started_at=wo_started,
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
