"""
Generate realistic demo data for 3D terminal visualization.

Creates:
- Container owners (major shipping lines)
- Companies (logistics/trading businesses)
- Containers with proper ISO types
- Container entries with realistic dwell times
- Auto-assigns positions via placement service

Usage:
    python manage.py generate_demo_data              # Default: 80% capacity
    python manage.py generate_demo_data --capacity 60  # 60% capacity
    python manage.py generate_demo_data --clear      # Clear existing data first
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Company, CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import (
    ContainerEntry,
    ContainerOwner,
    ContainerPosition,
)


# =============================================================================
# REALISTIC DATA CONSTANTS
# =============================================================================

# Major shipping lines (container owners)
SHIPPING_LINES = [
    "MAERSK",
    "MSC",
    "COSCO",
    "CMA CGM",
    "Hapag-Lloyd",
    "ONE",
    "Evergreen",
    "Yang Ming",
    "HMM",
    "ZIM",
    "PIL",
    "Wan Hai",
    "OOCL",
    "Sinokor",
    "SITC",
]

# Container prefixes for each shipping line (4 letters)
SHIPPING_LINE_PREFIXES = {
    "MAERSK": ["MAEU", "MSKU", "MRKU", "MRSU"],
    "MSC": ["MSCU", "MEDU", "MSNU"],
    "COSCO": ["CSLU", "CCLU", "COSU"],
    "CMA CGM": ["CMAU", "CGMU"],
    "Hapag-Lloyd": ["HLXU", "HLCU"],
    "ONE": ["ONEY", "ONEU"],
    "Evergreen": ["EGHU", "EISU", "EITU"],
    "Yang Ming": ["YMLU", "YMMU"],
    "HMM": ["HDMU", "HMMU"],
    "ZIM": ["ZIMU", "ZCSU"],
    "PIL": ["PCIU", "PILU"],
    "Wan Hai": ["WHLU", "WANU"],
    "OOCL": ["OOLU", "OOCL"],
    "Sinokor": ["SKHU", "SEKU"],
    "SITC": ["STCU", "SITU"],
}

# Logistics/trading companies (customers)
COMPANY_NAMES = [
    "Trans Logistics Uzbekistan",
    "Global Trade Solutions",
    "Silk Road Cargo",
    "Orient Express Freight",
    "Central Asia Transport",
    "Euro-Asian Logistics",
    "Golden Bridge Trading",
    "Tashkent Freight Services",
    "Samarkand Import Export",
    "Continental Cargo",
    "Asia Connect Logistics",
    "Prime Shipping Agency",
]

# ISO type distribution (realistic mix)
# Format: (iso_type, weight) - higher weight = more common
ISO_TYPE_WEIGHTS = [
    # 20ft containers (~55% of total)
    ("22G1", 35),  # 20ft standard dry - most common
    ("22R1", 5),  # 20ft reefer
    ("22U1", 3),  # 20ft open top
    ("22P1", 2),  # 20ft flat rack
    # 40ft containers (~35% of total)
    ("42G1", 20),  # 40ft standard dry
    ("45G1", 10),  # 40ft high cube - very popular
    ("42R1", 3),  # 40ft reefer
    ("45R1", 2),  # 40ft HC reefer
    # 45ft containers (~10% of total)
    ("L5G1", 8),  # 45ft HC dry
    ("L5R1", 2),  # 45ft HC reefer
]

# Common cargo names
CARGO_NAMES = [
    "Текстиль",
    "Электроника",
    "Строительные материалы",
    "Продукты питания",
    "Машины и оборудование",
    "Химическая продукция",
    "Мебель",
    "Автозапчасти",
    "Одежда и обувь",
    "Бытовая техника",
    "Медицинские товары",
    "Сельхозпродукция",
    "Металлопрокат",
    "Пластик и полимеры",
    "",  # Some containers have no cargo name
]

# Destination stations
DESTINATION_STATIONS = [
    "Ташкент-Товарный",
    "Бухара",
    "Самарканд",
    "Фергана",
    "Навои",
    "Термез",
    "Андижан",
    "Нукус",
    "Карши",
    "",  # Some don't have destination
]

# Transport number prefixes
TRUCK_PREFIXES = ["01", "10", "20", "30", "40", "50", "60", "70", "80", "90"]
TRUCK_REGIONS = ["A", "B", "C", "D", "E", "F", "H", "K", "M", "X"]


def get_container_size(iso_type: str) -> str:
    """Get container size from ISO type code."""
    if not iso_type:
        return "20ft"
    first_char = iso_type[0]
    if first_char == "2":
        return "20ft"
    elif first_char == "4":
        return "40ft"
    elif first_char in ("L", "9"):
        return "45ft"
    return "20ft"


class Command(BaseCommand):
    help = "Generate realistic demo data for 3D terminal visualization"

    def add_arguments(self, parser):
        parser.add_argument(
            "--capacity",
            type=int,
            default=80,
            help="Target capacity percentage (default: 80)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before generating",
        )
        parser.add_argument(
            "--zone",
            type=str,
            default="A",
            help="Zone to fill (default: A)",
        )

    def handle(self, *args, **options):
        capacity = options["capacity"]
        zone = options["zone"].upper()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n🚛 Generating Demo Data for Terminal Zone {zone}"
            )
        )
        self.stdout.write(f"   Target capacity: {capacity}%\n")

        with transaction.atomic():
            if options["clear"]:
                self._clear_existing_data()

            # Step 1: Create container owners
            owners = self._create_container_owners()

            # Step 2: Create companies
            companies = self._create_companies()

            # Step 3: Get or create admin user for recorded_by
            admin_user = self._get_admin_user()

            # Step 4: Calculate target container count
            # Zone A: 10 rows × 10 bays × 4 tiers = 400 slots
            # But considering row segregation and 40ft space needs: ~300 effective
            max_capacity = 300  # Realistic max for Zone A
            target_count = int(max_capacity * capacity / 100)

            self.stdout.write("\n📊 Capacity Planning:")
            self.stdout.write(f"   Max realistic capacity: {max_capacity} containers")
            self.stdout.write(f"   Target ({capacity}%): {target_count} containers")

            # Step 5: Generate containers and entries
            entries = self._generate_containers_and_entries(
                target_count=target_count,
                owners=owners,
                companies=companies,
                admin_user=admin_user,
            )

            # Step 6: Auto-assign positions
            self._assign_positions(entries, zone)

            # Summary
            self._print_summary(zone)

    def _clear_existing_data(self):
        """Clear existing demo data."""
        self.stdout.write("\n🗑️  Clearing existing data...")

        # Clear positions first (due to FK constraints)
        pos_count = ContainerPosition.objects.all().delete()[0]
        self.stdout.write(f"   Deleted {pos_count} positions")

        # Clear entries
        entry_count = ContainerEntry.objects.all().delete()[0]
        self.stdout.write(f"   Deleted {entry_count} entries")

        # Clear containers
        container_count = Container.objects.all().delete()[0]
        self.stdout.write(f"   Deleted {container_count} containers")

        # Clear owners
        owner_count = ContainerOwner.objects.all().delete()[0]
        self.stdout.write(f"   Deleted {owner_count} owners")

        # Clear companies (only auto-generated ones)
        company_count = Company.objects.filter(name__in=COMPANY_NAMES).delete()[0]
        self.stdout.write(f"   Deleted {company_count} demo companies")

    def _create_container_owners(self) -> list[ContainerOwner]:
        """Create major shipping lines as container owners."""
        self.stdout.write("\n🏢 Creating container owners (shipping lines)...")

        owners = []
        created_count = 0

        for name in SHIPPING_LINES:
            owner, created = ContainerOwner.objects.get_or_create(
                name=name, defaults={"slug": name.lower().replace(" ", "-")}
            )
            owners.append(owner)
            if created:
                created_count += 1

        self.stdout.write(f"   ✓ {len(owners)} shipping lines ({created_count} new)")
        return owners

    def _create_companies(self) -> list[Company]:
        """Create logistics/trading companies."""
        self.stdout.write("\n🏭 Creating companies...")

        companies = []
        created_count = 0

        for name in COMPANY_NAMES:
            company, created = Company.objects.get_or_create(
                name=name, defaults={"is_active": True}
            )
            companies.append(company)
            if created:
                created_count += 1

        self.stdout.write(f"   ✓ {len(companies)} companies ({created_count} new)")
        return companies

    def _get_admin_user(self) -> CustomUser:
        """Get or create admin user for recorded_by field."""
        admin, created = CustomUser.objects.get_or_create(
            username="demo_admin",
            defaults={
                "user_type": "admin",
                "is_staff": True,
                "first_name": "Demo",
                "last_name": "Admin",
            },
        )
        if created:
            admin.set_password("demo123")
            admin.save()
        return admin

    def _generate_containers_and_entries(
        self,
        target_count: int,
        owners: list[ContainerOwner],
        companies: list[Company],
        admin_user: CustomUser,
    ) -> list[ContainerEntry]:
        """Generate containers with entries."""
        self.stdout.write(f"\n📦 Generating {target_count} containers...")

        entries = []
        now = timezone.now()

        # Build weighted ISO type list for random selection
        iso_types = []
        for iso_type, weight in ISO_TYPE_WEIGHTS:
            iso_types.extend([iso_type] * weight)

        # Status distribution: ~70% laden, ~30% empty
        status_weights = ["LADEN"] * 70 + ["EMPTY"] * 30

        # Transport type distribution: ~80% truck, ~15% wagon, ~5% train
        transport_weights = ["TRUCK"] * 80 + ["WAGON"] * 15 + ["TRAIN"] * 5

        for i in range(target_count):
            # Select random owner and their prefix
            owner = random.choice(owners)
            prefix = random.choice(SHIPPING_LINE_PREFIXES.get(owner.name, ["XXXX"]))

            # Generate unique container number
            while True:
                number = f"{prefix}{random.randint(1000000, 9999999)}"
                if not Container.objects.filter(container_number=number).exists():
                    break

            # Random ISO type
            iso_type = random.choice(iso_types)

            # Create container
            container = Container.objects.create(
                container_number=number,
                iso_type=iso_type,
            )

            # Random entry time (last 30 days, weighted toward recent)
            # More containers entered recently for realistic visualization
            days_ago = int(abs(random.gauss(7, 10)))  # Mean 7 days, std 10
            days_ago = min(days_ago, 30)  # Cap at 30 days
            entry_time = now - timedelta(
                days=days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # Status and transport
            status = random.choice(status_weights)
            transport_type = random.choice(transport_weights)

            # Generate transport number
            if transport_type == "TRUCK":
                transport_number = (
                    f"{random.choice(TRUCK_PREFIXES)}"
                    f"{random.choice(TRUCK_REGIONS)}"
                    f"{random.randint(100, 999)}"
                    f"{random.choice(TRUCK_REGIONS)}"
                    f"{random.choice(TRUCK_REGIONS)}"
                )
            elif transport_type == "WAGON":
                transport_number = f"ВГ-{random.randint(10000, 99999)}"
            else:  # TRAIN
                transport_number = f"П-{random.randint(1000, 9999)}"

            # Company assignment (~80% have company, ~20% just client_name)
            company = None
            client_name = ""
            if random.random() < 0.8:
                company = random.choice(companies)
            else:
                client_name = random.choice(
                    [
                        "ИП Алиев А.А.",
                        "ООО Восток-Запад",
                        "ЧП Караванщик",
                        "ИП Рахимов Р.Р.",
                        "ООО Транзит-Сервис",
                    ]
                )

            # Cargo for laden containers
            cargo_name = ""
            cargo_weight = None
            if status == "LADEN":
                cargo_name = random.choice(CARGO_NAMES)
                # Weight between 5 and 28 tons (container limits)
                cargo_weight = Decimal(str(round(random.uniform(5.0, 28.0), 2)))

            # Create entry
            entry = ContainerEntry.objects.create(
                container=container,
                entry_time=entry_time,
                status=status,
                transport_type=transport_type,
                transport_number=transport_number,
                recorded_by=admin_user,
                client_name=client_name,
                company=company,
                container_owner=owner,
                cargo_name=cargo_name,
                cargo_weight=cargo_weight,
                destination_station=random.choice(DESTINATION_STATIONS),
            )
            entries.append(entry)

            # Progress indicator every 50 containers
            if (i + 1) % 50 == 0:
                self.stdout.write(f"   ... {i + 1}/{target_count} containers")

        # Statistics
        laden_count = sum(1 for e in entries if e.status == "LADEN")
        empty_count = len(entries) - laden_count

        size_counts = {"20ft": 0, "40ft": 0, "45ft": 0}
        for entry in entries:
            size = get_container_size(entry.container.iso_type)
            size_counts[size] += 1

        self.stdout.write(f"\n   ✓ Created {len(entries)} container entries:")
        self.stdout.write(f"     Status: {laden_count} laden, {empty_count} empty")
        self.stdout.write(
            f"     Sizes: {size_counts['20ft']} × 20ft, "
            f"{size_counts['40ft']} × 40ft, {size_counts['45ft']} × 45ft"
        )

        return entries

    def _assign_positions(self, entries: list[ContainerEntry], zone: str):
        """Assign positions to entries using ISO stacking rules."""
        self.stdout.write(f"\n📍 Assigning positions in Zone {zone}...")

        # Sort entries for proper stacking:
        # 1. Laden first (go at bottom)
        # 2. 40ft/45ft before 20ft
        entries.sort(
            key=lambda e: (
                0 if e.status == "LADEN" else 1,
                0
                if get_container_size(e.container.iso_type) in ("40ft", "45ft")
                else 1,
            )
        )

        max_rows = 10
        max_bays = 10
        max_tiers = 4

        # Row segregation: 1-5 for 40ft, 6-10 for 20ft
        rows_40ft = [1, 2, 3, 4, 5]
        rows_20ft = [6, 7, 8, 9, 10]

        # Track positions: (row, bay, tier, sub_slot) -> ContainerEntry
        positions = {}
        assigned = 0
        skipped = 0

        for entry in entries:
            container_size = get_container_size(entry.container.iso_type)
            is_laden = entry.status == "LADEN"

            # Determine valid rows and sub-slots based on size
            if container_size in ("40ft", "45ft"):
                valid_rows = rows_40ft
                valid_slots = ["A"]  # 40ft containers always use slot A
            else:
                valid_rows = rows_20ft
                valid_slots = ["A", "B"]  # 20ft can use both slots

            # Find valid position
            position = self._find_valid_position(
                container_size=container_size,
                is_laden=is_laden,
                valid_rows=valid_rows,
                valid_slots=valid_slots,
                positions=positions,
                max_bays=max_bays,
                max_tiers=max_tiers,
            )

            if position is None:
                skipped += 1
                continue

            row, bay, tier, sub_slot = position

            # Create position record
            ContainerPosition.objects.create(
                container_entry=entry,
                zone=zone,
                row=row,
                bay=bay,
                tier=tier,
                sub_slot=sub_slot,
                auto_assigned=True,
            )

            # Update location field for legacy display
            coord = f"{zone}-R{row:02d}-B{bay:02d}-T{tier}-{sub_slot}"
            entry.location = coord
            entry.save(update_fields=["location"])

            positions[(row, bay, tier, sub_slot)] = entry
            assigned += 1

        self.stdout.write(f"   ✓ Assigned {assigned} positions")
        if skipped:
            self.stdout.write(
                self.style.WARNING(f"   ⚠ Skipped {skipped} (no valid position)")
            )

    def _find_valid_position(
        self,
        container_size: str,
        is_laden: bool,
        valid_rows: list[int],
        valid_slots: list[str],
        positions: dict,
        max_bays: int,
        max_tiers: int,
    ) -> tuple | None:
        """Find valid position following ISO stacking rules with sub-slots."""
        # Strategy: fill bottom-up, consolidate stacks
        preferred_stack_height = 3  # Stack to 3 before spreading

        # Try to stack on existing containers first (consolidation)
        for row in valid_rows:
            for bay in range(1, max_bays + 1):
                for sub_slot in valid_slots:
                    # Find current stack height at this position
                    current_tier = 0
                    for tier in range(1, max_tiers + 1):
                        if (row, bay, tier, sub_slot) in positions:
                            current_tier = tier
                        else:
                            break

                    # Skip if already at max or preferred height
                    if current_tier >= max_tiers:
                        continue
                    if current_tier >= preferred_stack_height:
                        continue

                    next_tier = current_tier + 1

                    # Check stacking rules if stacking on existing
                    if current_tier > 0:
                        below = positions[(row, bay, current_tier, sub_slot)]
                        below_size = get_container_size(below.container.iso_type)
                        below_laden = below.status == "LADEN"

                        # Rule: 40ft/45ft cannot stack on 20ft
                        if container_size in ("40ft", "45ft") and below_size == "20ft":
                            continue

                        # Rule: Laden cannot stack on empty
                        if is_laden and not below_laden:
                            continue

                    return (row, bay, next_tier, sub_slot)

        # If no consolidation possible, find any empty ground slot
        attempts = [
            (r, b, s)
            for r in valid_rows
            for b in range(1, max_bays + 1)
            for s in valid_slots
        ]
        random.shuffle(attempts)

        for row, bay, sub_slot in attempts:
            if (row, bay, 1, sub_slot) not in positions:
                return (row, bay, 1, sub_slot)

        # Try higher tiers if ground is full
        for row, bay, sub_slot in attempts:
            for tier in range(2, max_tiers + 1):
                if (row, bay, tier, sub_slot) in positions:
                    continue
                if (row, bay, tier - 1, sub_slot) not in positions:
                    continue  # Need support

                below = positions[(row, bay, tier - 1, sub_slot)]
                below_size = get_container_size(below.container.iso_type)
                below_laden = below.status == "LADEN"

                if container_size in ("40ft", "45ft") and below_size == "20ft":
                    continue
                if is_laden and not below_laden:
                    continue

                return (row, bay, tier, sub_slot)

        return None

    def _print_summary(self, zone: str):
        """Print final summary statistics."""
        self.stdout.write(self.style.MIGRATE_HEADING("\n📊 Final Summary"))

        # Count by zone
        total_positioned = ContainerPosition.objects.filter(zone=zone).count()
        total_entries = ContainerEntry.objects.filter(exit_date__isnull=True).count()

        # Status breakdown
        laden = ContainerEntry.objects.filter(
            exit_date__isnull=True, status="LADEN"
        ).count()
        empty = ContainerEntry.objects.filter(
            exit_date__isnull=True, status="EMPTY"
        ).count()

        # Size breakdown from positions
        positions = ContainerPosition.objects.filter(zone=zone).select_related(
            "container_entry__container"
        )
        size_counts = {"20ft": 0, "40ft": 0, "45ft": 0}
        for pos in positions:
            size = get_container_size(pos.container_entry.container.iso_type)
            size_counts[size] += 1

        # Dwell time distribution
        now = timezone.now()
        dwell_buckets = {"0-3d": 0, "4-7d": 0, "8-14d": 0, "15-21d": 0, "21+d": 0}
        for pos in positions:
            days = (now - pos.container_entry.entry_time).days
            if days <= 3:
                dwell_buckets["0-3d"] += 1
            elif days <= 7:
                dwell_buckets["4-7d"] += 1
            elif days <= 14:
                dwell_buckets["8-14d"] += 1
            elif days <= 21:
                dwell_buckets["15-21d"] += 1
            else:
                dwell_buckets["21+d"] += 1

        # Capacity calculation
        max_capacity = 300
        occupancy = round(total_positioned / max_capacity * 100, 1)

        self.stdout.write(f"\n   Zone {zone} Statistics:")
        self.stdout.write(f"   ├── Total containers: {total_positioned}")
        self.stdout.write(
            f"   ├── Occupancy: {occupancy}% ({total_positioned}/{max_capacity})"
        )
        self.stdout.write("   │")
        self.stdout.write("   ├── By Status:")
        self.stdout.write(f"   │   ├── Laden: {laden}")
        self.stdout.write(f"   │   └── Empty: {empty}")
        self.stdout.write("   │")
        self.stdout.write("   ├── By Size:")
        self.stdout.write(f"   │   ├── 20ft: {size_counts['20ft']}")
        self.stdout.write(f"   │   ├── 40ft: {size_counts['40ft']}")
        self.stdout.write(f"   │   └── 45ft: {size_counts['45ft']}")
        self.stdout.write("   │")
        self.stdout.write("   └── By Dwell Time:")
        self.stdout.write(f"       ├── 0-3 days:  {dwell_buckets['0-3d']} (green)")
        self.stdout.write(f"       ├── 4-7 days:  {dwell_buckets['4-7d']} (yellow)")
        self.stdout.write(f"       ├── 8-14 days: {dwell_buckets['8-14d']} (orange)")
        self.stdout.write(f"       ├── 15-21 days: {dwell_buckets['15-21d']} (red)")
        self.stdout.write(f"       └── 21+ days:  {dwell_buckets['21+d']} (purple)")

        self.stdout.write(self.style.SUCCESS("\n✅ Demo data generated successfully!"))
        self.stdout.write("   View in 3D at: http://localhost:5174/placement\n")
