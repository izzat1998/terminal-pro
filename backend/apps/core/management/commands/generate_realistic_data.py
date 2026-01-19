"""
Generate 90 days of realistic presentation data for MTT Container Terminal.

This script creates a complete operational history with all logical chains:
- PreOrder → ContainerEntry → WorkOrder → ContainerPosition → Exit
- Realistic distributions (70/30 ratios for empty/laden, truck/train, 40ft/20ft)
- Container reuse (same containers return multiple times)
- Train batch arrivals (5-15 containers with same train number)
- Company grouping in 3D yard
- Complete audit trail with realistic timestamps
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
    help = "Generate 90 days of realistic presentation data with complete audit trails"

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

        self.stdout.write(self.style.NOTICE(f"🚀 Starting realistic data generation for {days} days...\n"))

        if options["clear"] and not self.dry_run:
            self._clear_operational_data()

        # Initialize state tracking
        self.stats = {
            "containers_created": 0,
            "entries_created": 0,
            "preorders_created": 0,
            "work_orders_created": 0,
            "positions_created": 0,
            "exits_processed": 0,
        }

        with transaction.atomic():
            # Phase 1: Foundation data
            self._log_phase("Phase 1: Creating foundation data (users, companies, vehicles, tariffs)")
            foundation = self._create_foundation_data()

            # Phase 2: Container pool
            self._log_phase("Phase 2: Creating container pool")
            container_pool = self._create_container_pool(100)

            # Phase 3: State management setup
            self._log_phase("Phase 3: Initializing state management")
            state = self._initialize_state(foundation)

            # Phase 4: Chronological generation (day by day)
            self._log_phase(f"Phase 4: Generating {days} days of operations")
            self._generate_timeline(days, foundation, container_pool, state)

            if self.dry_run:
                self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - Rolling back transaction\n"))
                raise Exception("Dry run - transaction rolled back")

        # Final statistics
        self._print_statistics()

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

        # 1. Create admin users for work order management
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

        # 2. Create companies with realistic Uzbek names
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

        # 3. Create managers with realistic Uzbek names
        managers_data = [
            {"first_name": "Aziz", "last_name": "Karimov", "phone": "+998901234567"},
            {"first_name": "Bobur", "last_name": "Toshmatov", "phone": "+998902345678"},
            {"first_name": "Sardor", "last_name": "Normatov", "phone": "+998903456789"},
            {"first_name": "Dilshod", "last_name": "Saidov", "phone": "+998904567890"},
        ]

        foundation["managers"] = []
        for i, data in enumerate(managers_data):
            user = self._get_or_create_user(
                username=f"{data['first_name'].lower()}_manager",
                user_type="manager",
                first_name=data["first_name"],
                last_name=data["last_name"],
            )

            # Create manager profile with telegram_user_id
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

        # 5. Create container owners (shipping lines)
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

        # 6. Create terminal vehicles (reach stackers)
        vehicles_data = [
            {"name": "RS-01", "operator": "Aziz"},
            {"name": "RS-02", "operator": "Bobur"},
            {"name": "RS-03", "operator": "Sardor"},
        ]

        foundation["vehicles"] = []
        for i, data in enumerate(vehicles_data):
            operator = foundation["managers"][i % len(foundation["managers"])]
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

        # 7. Create tariffs covering full period
        self._create_tariffs(foundation["companies"])

        return foundation

    def _create_tariffs(self, companies: List[Company]):
        """Create tariffs covering the full 90+ day period"""
        start_date = timezone.now().date() - timedelta(days=100)

        # Get or create system admin for tariff created_by field
        system_admin = User.objects.filter(user_type="admin", username="system").first()
        if not system_admin:
            system_admin = User.objects.filter(user_type="admin").first()

        # General tariff (applies to all companies without special tariff)
        general_tariff, created = Tariff.objects.get_or_create(
            company=None,
            effective_from=start_date,
            defaults={
                "created_by": system_admin,
                "notes": "General tariff for all companies",
            },
        )

        if created:
            # Create rates for all size/status combinations
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

        # Company-specific tariffs (better rates for first 2 companies)
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
                # Better rates with more free days
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

        # ISO types with correct size matching (from Container.ISO_TYPE_CHOICES)
        iso_types_40ft = ["42G1", "45G1", "45R1", "L5G1", "42R1", "42U1", "42P1", "42T1"]  # 4/L = 40ft
        iso_types_20ft = ["22G1", "22R1", "22K2", "25G1", "22U1", "22P1", "22T1"]  # 2 = 20ft

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
        """Initialize state tracking for chronological generation"""
        state = {
            # Occupancy grid: key = (zone, row, bay, tier, slot), value = entry_id
            "occupancy_grid": {},
            # Container exit tracking: key = container_id, value = exit_date
            "container_exits": {},
            # Company row assignments: key = company_id, value = {"40ft": [rows], "20ft": [rows]}
            "company_rows": {},
            # Active containers on terminal: set of entry_ids
            "active_entries": set(),
            # Containers available for reuse: set of container_ids
            "available_containers": set(),
        }

        # Assign rows to companies
        row_40ft_available = list(range(1, 6))  # Rows 1-5 for 40ft
        row_20ft_available = list(range(6, 11))  # Rows 6-10 for 20ft

        for company in foundation["companies"]:
            size = foundation["company_sizes"][company.id]

            if size == "large" and len(row_40ft_available) >= 2 and len(row_20ft_available) >= 2:
                # Large companies: 2 rows each
                state["company_rows"][company.id] = {
                    "40ft": [row_40ft_available.pop(0), row_40ft_available.pop(0)],
                    "20ft": [row_20ft_available.pop(0), row_20ft_available.pop(0)],
                }
            elif size == "medium" and len(row_40ft_available) >= 1 and len(row_20ft_available) >= 1:
                # Medium companies: 1 row each
                state["company_rows"][company.id] = {
                    "40ft": [row_40ft_available.pop(0)],
                    "20ft": [row_20ft_available.pop(0)],
                }
            else:
                # Small companies or overflow: use general pool
                state["company_rows"][company.id] = {"40ft": [], "20ft": []}

        self._log_item("Initialized state tracking with company row assignments")
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

            # Determine if today has train arrivals (30% of volume)
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
            self._process_exits(current_date, state)

            if self.verbosity >= 2 and day_offset % 10 == 0:
                self.stdout.write(f"  Day {day_offset + 1}/{days}: {len(train_entries) + len(truck_entries)} entries created")

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
        preorder = None
        if random.random() < 0.7:
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

            # Create work order and placement
            self._create_work_order_and_placement(entry, entry_time, foundation, state)

            state["active_entries"].add(entry.id)

            return entry

        return None

    def _select_container(
        self, container_pool: List[Container], state: Dict[str, Any]
    ) -> Optional[Container]:
        """Select container from pool, allowing reuse after exit"""

        # 20-30% chance to reuse a container that has exited
        if state["available_containers"] and random.random() < 0.25:
            container_id = random.choice(list(state["available_containers"]))
            return Container.objects.get(id=container_id)

        # Otherwise use from pool
        return random.choice(container_pool)

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

    def _create_work_order_and_placement(
        self,
        entry: ContainerEntry,
        entry_time: datetime,
        foundation: Dict[str, Any],
        state: Dict[str, Any],
    ):
        """Create work order and placement with realistic timeline"""

        # Find suitable position
        position_coords = self._find_suitable_position(entry, foundation, state)
        if not position_coords:
            self._log_item(f"⚠️  No suitable position found for entry {entry.id}")
            return

        zone, row, bay, tier, slot = position_coords

        # Create work order (98% success, 0% fail, 2% pending)
        # Zero failures for clean demo presentation
        # Only recent entries (last 2 days) can be pending to show "active operations"
        now = timezone.now()
        days_since_entry = (now.date() - entry_time.date()).days

        # Only entries from last 2 days can be pending (shows active workflow)
        if days_since_entry <= 2:
            outcome = random.choices(["success", "pending"], weights=[98, 2])[0]
        else:
            outcome = "success"  # Historical entries are all completed

        created_at = entry_time + timedelta(minutes=random.randint(5, 30))
        assigned_at = created_at + timedelta(minutes=random.randint(2, 10))
        accepted_at = assigned_at + timedelta(minutes=random.randint(1, 5))
        started_at = accepted_at + timedelta(minutes=random.randint(1, 3))

        if outcome == "success":
            completed_at = started_at + timedelta(minutes=random.randint(5, 20))
            verified_at = completed_at + timedelta(minutes=random.randint(2, 10))
            final_status = "VERIFIED"
        else:  # pending
            completed_at = None
            verified_at = None
            final_status = random.choice(["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"])

        vehicle = random.choice(foundation["vehicles"])

        if not self.dry_run:
            # Calculate realistic SLA deadline based on work order outcome
            # This ensures historical data has realistic SLA metrics (some met, some missed)
            sla_minutes = 60

            if outcome == "success":
                # Successful work orders: 80% met SLA, 20% missed but still completed
                if random.random() < 0.8:
                    # SLA met: deadline was after completion
                    sla_deadline = verified_at + timedelta(minutes=random.randint(5, 30))
                else:
                    # SLA missed: deadline was before completion
                    sla_deadline = started_at + timedelta(minutes=random.randint(30, 50))
            elif outcome == "fail":
                # Failed work orders: 50% met deadline before failure, 50% missed
                if random.random() < 0.5:
                    sla_deadline = completed_at + timedelta(minutes=random.randint(5, 30))
                else:
                    sla_deadline = started_at + timedelta(minutes=random.randint(20, 40))
            else:  # pending
                # Pending work orders: Some should be expired, some not yet
                # Use current time to determine if SLA should be expired
                now = timezone.now()
                time_since_created = (now - created_at).total_seconds() / 60

                if time_since_created > sla_minutes:
                    # Old pending work order - should be expired
                    sla_deadline = created_at + timedelta(minutes=sla_minutes)
                else:
                    # Recent pending work order - deadline in future
                    sla_deadline = created_at + timedelta(minutes=sla_minutes)

            # Create work order without timestamps (they get auto-set by TimestampedModel)
            work_order = WorkOrder.objects.create(
                container_entry=entry,
                priority="MEDIUM",
                status=final_status,
                assigned_to_vehicle=vehicle,
                created_by=foundation["controlroom_admin"],
                target_zone=zone,
                target_row=row,
                target_bay=bay,
                target_tier=tier,
                target_sub_slot=slot,
                sla_deadline=sla_deadline,
            )

            # Update timestamps separately to bypass TimestampedModel's auto-setting
            # This ensures chronological order: created_at < assigned_at < accepted_at < started_at < completed_at < verified_at
            WorkOrder.objects.filter(id=work_order.id).update(
                created_at=created_at,
                assigned_at=assigned_at,
                accepted_at=accepted_at,
                started_at=started_at,
                completed_at=completed_at,
                verified_at=verified_at,
            )

            self.stats["work_orders_created"] += 1

            # Create position if work order succeeded
            if final_status in ["COMPLETED", "VERIFIED"]:
                position = ContainerPosition.objects.create(
                    container_entry=entry,
                    zone=zone,
                    row=row,
                    bay=bay,
                    tier=tier,
                    sub_slot=slot,
                )

                # Update entry location
                entry.location = f"{zone}-R{row:02d}-B{bay:02d}-T{tier}-{slot}"
                entry.save(update_fields=["location"])

                # Mark position as occupied
                state["occupancy_grid"][(zone, row, bay, tier, slot)] = entry.id
                self.stats["positions_created"] += 1

    def _find_suitable_position(
        self,
        entry: ContainerEntry,
        foundation: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Optional[Tuple[str, int, int, int, str]]:
        """
        Find suitable 3D position with company-aware grouping.

        Algorithm (4-tier fallback):
        1. Company's assigned rows (80-90% success - creates visual clusters)
        2. Adjacent rows in same size area (overflow with proximity)
        3. Any row in same size area (maintains TOS standards)
        4. Emergency fallback (any available row)
        """

        # Determine container size from ISO type
        iso_type = entry.container.iso_type
        size_code = iso_type[0] if iso_type else "2"
        is_40ft = size_code in ["4", "L"]

        # Get company's assigned rows
        company_id = entry.company.id if entry.company else None
        company_rows = state["company_rows"].get(company_id, {"40ft": [], "20ft": []})

        # Define size area ranges
        size_area_rows = list(range(1, 6)) if is_40ft else list(range(6, 11))

        # Tier 1: Try company's assigned rows FIRST (creates company clusters)
        company_assigned = company_rows["40ft"] if is_40ft else company_rows["20ft"]
        if company_assigned:
            position = self._try_rows(company_assigned, is_40ft, state)
            if position:
                return position

        # Tier 2: Try adjacent rows (overflow with visual proximity)
        if company_assigned:
            adjacent_rows = self._get_adjacent_rows(company_assigned, size_area_rows)
            position = self._try_rows(adjacent_rows, is_40ft, state)
            if position:
                return position

        # Tier 3: Try any row in same size area (maintains TOS standards)
        position = self._try_rows(size_area_rows, is_40ft, state)
        if position:
            return position

        # Tier 4: Emergency fallback - try any row (ensures placement always succeeds)
        all_rows = list(range(1, 11))
        position = self._try_rows(all_rows, is_40ft, state)
        return position

    def _get_adjacent_rows(self, assigned_rows: list, size_area_rows: list) -> list:
        """Get rows adjacent to company's assigned rows within size area."""
        if not assigned_rows:
            return []

        adjacent = set()
        for row in assigned_rows:
            # Add ±1 and ±2 rows
            for offset in [-2, -1, 1, 2]:
                adjacent_row = row + offset
                if adjacent_row in size_area_rows and adjacent_row not in assigned_rows:
                    adjacent.add(adjacent_row)

        return sorted(list(adjacent))

    def _try_rows(
        self,
        rows: list,
        is_40ft: bool,
        state: Dict[str, Any],
        max_attempts: int = 200
    ) -> Optional[Tuple[str, int, int, int, str]]:
        """Try to find available position in given rows."""
        if not rows:
            return None

        zone = "A"
        # Use tiers 1-2 for more capacity (tier 1 preferred, tier 2 as overflow)
        tiers = [1, 2]

        for _ in range(max_attempts):
            row = random.choice(rows)
            bay = random.randint(1, 10)
            slot = "A" if is_40ft else random.choice(["A", "B"])
            tier = random.choice(tiers)

            # Check if position is occupied
            if (zone, row, bay, tier, slot) not in state["occupancy_grid"]:
                # For tier 2, verify tier 1 support exists
                if tier == 2:
                    if (zone, row, bay, 1, slot) in state["occupancy_grid"]:
                        return (zone, row, bay, tier, slot)
                else:
                    return (zone, row, bay, tier, slot)

        return None

    def _process_exits(self, current_date: datetime, state: Dict[str, Any]):
        """Process container exits for current day"""

        # Decide which containers exit today (mixed pattern: 50% quick, 50% longer)
        for entry_id in list(state["active_entries"]):
            if self.dry_run:
                continue

            entry = ContainerEntry.objects.get(id=entry_id)
            days_on_terminal = (current_date.date() - entry.entry_time.date()).days

            # Quick exit (1-3 days) or longer stay (4-30 days)
            # Increased exit rates to maintain terminal capacity for demos
            should_exit = False
            if days_on_terminal >= 1 and days_on_terminal <= 3 and random.random() < 0.35:
                should_exit = True  # 35% chance for quick exit (up from 20%)
            elif days_on_terminal >= 4 and days_on_terminal <= 7 and random.random() < 0.20:
                should_exit = True  # 20% chance for medium stays (up from 5%)
            elif days_on_terminal >= 8 and random.random() < 0.30:
                should_exit = True  # 30% chance for long stays (keep terminal flowing)

            if should_exit:
                exit_time = current_date.replace(hour=random.randint(8, 20), minute=random.randint(0, 59))
                exit_transport_type = random.choice(["TRUCK", "TRAIN"])

                if exit_transport_type == "TRUCK":
                    region = random.choice(["01", "10", "20", "30"])
                    exit_transport_number = f"{region}{random.choice('ABCD')}{random.randint(100, 999)}{random.choice('EF')}{random.choice('GH')}"
                else:
                    exit_transport_number = f"W{random.randint(100000, 999999)}"
                    entry.exit_train_number = f"T{random.randint(1000, 9999)}"

                entry.exit_date = exit_time
                entry.exit_transport_type = exit_transport_type
                entry.exit_transport_number = exit_transport_number
                entry.destination_station = random.choice([
                    "Toshkent-Tovarniy", "Chukursay", "Sergeli", "Bekabad"
                ])
                entry.location = ""  # Clear location
                entry.save()

                # Delete position
                ContainerPosition.objects.filter(container_entry=entry).delete()

                # Free occupancy grid
                for key, value in list(state["occupancy_grid"].items()):
                    if value == entry_id:
                        del state["occupancy_grid"][key]

                # Mark container as available for reuse
                state["available_containers"].add(entry.container.id)
                state["active_entries"].remove(entry_id)

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
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("📊 GENERATION COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"\n  Containers created: {self.stats['containers_created']}")
        self.stdout.write(f"  Container entries: {self.stats['entries_created']}")
        self.stdout.write(f"  Pre-orders created: {self.stats['preorders_created']}")
        self.stdout.write(f"  Work orders created: {self.stats['work_orders_created']}")
        self.stdout.write(f"  Positions created: {self.stats['positions_created']}")
        self.stdout.write(f"  Exits processed: {self.stats['exits_processed']}")
        self.stdout.write(f"\n  Containers on terminal: {self.stats['entries_created'] - self.stats['exits_processed']}")
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60 + "\n"))
