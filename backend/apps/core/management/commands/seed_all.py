"""
Comprehensive seed command that creates test data with correct relationships.

Usage:
    python manage.py seed_all                    # Full seed with default counts
    python manage.py seed_all --clear            # Clear all data first
    python manage.py seed_all --minimal          # Small dataset for quick testing
    python manage.py seed_all --companies 10     # Custom company count

This command seeds ALL models in the correct dependency order:
1. FileCategories (no deps)
2. Destinations (no deps)
3. Companies (no deps)
4. ContainerOwners (no deps)
5. Users (admin, managers, customers) with Profiles
6. Containers
7. ContainerEntries (depends on: Container, User, ContainerOwner, Company)
8. CraneOperations (depends on: ContainerEntry)
9. VehicleEntries (depends on: User, Destination)
10. PreOrders (depends on: Customer User, VehicleEntry, ContainerEntry)
"""

import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import Company, CustomerProfile, CustomUser, ManagerProfile
from apps.containers.models import Container
from apps.files.models import FileCategory
from apps.terminal_operations.models import (
    ContainerEntry,
    ContainerOwner,
    CraneOperation,
    PreOrder,
)
from apps.vehicles.models import Destination, VehicleEntry


class Command(BaseCommand):
    help = "Seed database with comprehensive test data including all relationships"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing data before seeding",
        )
        parser.add_argument(
            "--minimal",
            action="store_true",
            help="Create minimal dataset (3 companies, 5 containers, etc.)",
        )
        parser.add_argument("--companies", type=int, default=5, help="Number of companies (default: 5)")
        parser.add_argument("--managers", type=int, default=8, help="Number of managers (default: 8)")
        parser.add_argument("--customers", type=int, default=10, help="Number of customers (default: 10)")
        parser.add_argument("--containers", type=int, default=50, help="Number of containers (default: 50)")
        parser.add_argument("--entries", type=int, default=100, help="Number of container entries (default: 100)")
        parser.add_argument("--vehicles", type=int, default=30, help="Number of vehicle entries (default: 30)")
        parser.add_argument("--preorders", type=int, default=20, help="Number of pre-orders (default: 20)")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 70))
        self.stdout.write(self.style.HTTP_INFO("  COMPREHENSIVE DATABASE SEEDING"))
        self.stdout.write(self.style.HTTP_INFO("=" * 70 + "\n"))

        # Apply minimal settings if requested
        if options["minimal"]:
            options.update(
                {
                    "companies": 3,
                    "managers": 3,
                    "customers": 5,
                    "containers": 10,
                    "entries": 20,
                    "vehicles": 10,
                    "preorders": 5,
                }
            )

        # Clear data if requested
        if options["clear"]:
            self._clear_all_data()

        # Seed in dependency order
        self._seed_file_categories()
        destinations = self._seed_destinations()
        container_owners = self._seed_container_owners()
        companies = self._seed_companies(options["companies"])
        admin_user = self._ensure_admin_user()
        managers = self._seed_managers(options["managers"], companies)
        customers = self._seed_customers(options["customers"], companies)
        containers = self._seed_containers(options["containers"])
        all_users = [admin_user] + managers
        entries = self._seed_container_entries(options["entries"], containers, all_users, container_owners, companies)
        self._seed_crane_operations(entries)
        vehicle_entries = self._seed_vehicle_entries(options["vehicles"], customers, managers, destinations)
        self._seed_preorders(options["preorders"], customers, vehicle_entries, entries)

        # Summary
        self._print_summary()

    def _clear_all_data(self):
        """Clear all seeded data in reverse dependency order"""
        self.stdout.write(self.style.WARNING("\nClearing existing data..."))

        PreOrder.objects.all().delete()
        CraneOperation.objects.all().delete()
        VehicleEntry.objects.all().delete()
        ContainerEntry.objects.all().delete()
        Container.objects.all().delete()
        CustomerProfile.objects.all().delete()
        ManagerProfile.objects.all().delete()
        CustomUser.objects.filter(is_superuser=False).delete()
        Company.objects.all().delete()
        ContainerOwner.objects.all().delete()
        Destination.objects.all().delete()
        # Don't clear FileCategories - they're system data

        self.stdout.write(self.style.SUCCESS("Data cleared!\n"))

    def _seed_file_categories(self):
        """Seed file categories (required for file uploads)"""
        self.stdout.write("Seeding file categories...")

        categories = [
            {
                "code": "container_image",
                "name": "Container Image",
                "description": "Photos and images of containers",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                "max_file_size_mb": 10,
            },
            {
                "code": "truck_photo",
                "name": "Truck Photo",
                "description": "Photos of trucks for pre-orders and vehicle entries",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                "max_file_size_mb": 10,
            },
            {
                "code": "general_document",
                "name": "General Document",
                "description": "General documents and files",
                "allowed_mime_types": [
                    "application/pdf",
                    "application/msword",
                    "image/jpeg",
                    "image/png",
                ],
                "max_file_size_mb": 15,
            },
        ]

        for cat_data in categories:
            FileCategory.objects.update_or_create(
                code=cat_data["code"],
                defaults=cat_data,
            )

        self.stdout.write(self.style.SUCCESS(f"  Created {len(categories)} file categories"))

    def _seed_destinations(self):
        """Seed terminal destinations with zones"""
        self.stdout.write("Seeding destinations...")

        destinations_data = [
            {"name": "KALMAR", "zone": "K1", "code": "kalmar-k1"},
            {"name": "Kran 45t", "zone": "K2", "code": "kran45t-k2"},
            {"name": "Bruschatka", "zone": "K3", "code": "bruschatka-k3"},
            {"name": "Remont", "zone": "K4", "code": "remont-k4"},
            {"name": "Garazh", "zone": "K5", "code": "garazh-k5"},
            {"name": "Holodilnik", "zone": "X1", "code": "holodilnik-x1"},
            {"name": "Podval", "zone": "P1", "code": "podval-p1"},
            {"name": "Sklad-1", "zone": "U1", "code": "sklad1-u1"},
            {"name": "Naves-2", "zone": "H2", "code": "naves2-h2"},
            {"name": "Naves-1", "zone": "H1", "code": "naves1-h1"},
            {"name": "Office", "zone": "O1", "code": "office-o1"},
        ]

        destinations = []
        for data in destinations_data:
            dest, _ = Destination.objects.get_or_create(
                code=data["code"],
                defaults={"name": data["name"], "zone": data["zone"]},
            )
            destinations.append(dest)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(destinations)} destinations"))
        return destinations

    def _seed_container_owners(self):
        """Seed container owners (shipping lines)"""
        self.stdout.write("Seeding container owners...")

        owners_data = [
            "Maersk Line",
            "MSC Mediterranean",
            "CMA CGM",
            "COSCO Shipping",
            "Hapag-Lloyd",
            "ONE (Ocean Network Express)",
            "Evergreen Marine",
            "Yang Ming",
        ]

        owners = []
        for name in owners_data:
            owner, _ = ContainerOwner.objects.get_or_create(
                name=name,
                defaults={"slug": slugify(name)},
            )
            owners.append(owner)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(owners)} container owners"))
        return owners

    def _seed_companies(self, count):
        """Seed customer companies"""
        self.stdout.write(f"Seeding {count} companies...")

        company_names = [
            "Tashkent Logistics LLC",
            "Silk Road Trading Co",
            "Central Asia Freight",
            "Uzbekistan Export Import",
            "Samarkand Cargo Services",
            "Fergana Valley Transport",
            "Bukhara Trading House",
            "Navoi Industrial Group",
            "Andijan Agro Export",
            "Khiva Heritage Goods",
            "Nukus Northern Trade",
            "Karshi Cotton Export",
            "Termez Border Logistics",
            "Urgench Textile Trade",
            "Namangan Fruit Export",
        ]

        companies = []
        for i in range(min(count, len(company_names))):
            name = company_names[i]
            company, _ = Company.objects.get_or_create(
                name=name,
                defaults={
                    "slug": slugify(name),
                    "is_active": True,
                },
            )
            companies.append(company)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(companies)} companies"))
        return companies

    def _ensure_admin_user(self):
        """Ensure admin user exists"""
        self.stdout.write("Ensuring admin user...")

        admin, created = CustomUser.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@terminal.com",
                "first_name": "Admin",
                "last_name": "User",
                "user_type": "admin",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()

        status = "created" if created else "exists"
        self.stdout.write(self.style.SUCCESS(f"  Admin user {status} (admin/admin123)"))
        return admin

    def _seed_managers(self, count, companies):
        """Seed manager users with profiles"""
        self.stdout.write(f"Seeding {count} managers...")

        manager_data = [
            {"first": "Akbar", "last": "Karimov", "phone": "+998901234501"},
            {"first": "Dilshod", "last": "Rakhimov", "phone": "+998901234502"},
            {"first": "Jasur", "last": "Toshmatov", "phone": "+998901234503"},
            {"first": "Sardor", "last": "Yusupov", "phone": "+998901234504"},
            {"first": "Rustam", "last": "Aliyev", "phone": "+998901234505"},
            {"first": "Timur", "last": "Nazarov", "phone": "+998901234506"},
            {"first": "Bobur", "last": "Ismoilov", "phone": "+998901234507"},
            {"first": "Sherzod", "last": "Qodirov", "phone": "+998901234508"},
            {"first": "Jahongir", "last": "Mirzayev", "phone": "+998901234509"},
            {"first": "Otabek", "last": "Sultonov", "phone": "+998901234510"},
        ]

        managers = []
        for i in range(min(count, len(manager_data))):
            data = manager_data[i]
            username = f"manager{i + 1}"

            # Create user
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@terminal.com",
                    "first_name": data["first"],
                    "last_name": data["last"],
                    "user_type": "manager",
                    "is_staff": True,
                    "is_active": True,
                    # Legacy fields (for compatibility)
                    "phone_number": data["phone"],
                    "bot_access": True,
                    "gate_access": i < 5,  # First 5 have gate access
                },
            )
            if created:
                user.set_password("manager123")
                user.save()

            # Create profile
            ManagerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": data["phone"],
                    "bot_access": True,
                    "gate_access": i < 5,
                    "company": random.choice(companies) if companies and i % 2 == 0 else None,
                    "telegram_user_id": 100000000 + i,  # Fake telegram ID
                },
            )
            managers.append(user)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(managers)} managers (manager1/manager123)"))
        return managers

    def _seed_customers(self, count, companies):
        """Seed customer users with profiles (linked to companies)"""
        self.stdout.write(f"Seeding {count} customers...")

        customer_data = [
            {"first": "Alisher", "last": "Usmanov", "phone": "+998901234601"},
            {"first": "Bekzod", "last": "Tashkenov", "phone": "+998901234602"},
            {"first": "Davron", "last": "Samarkandov", "phone": "+998901234603"},
            {"first": "Eldor", "last": "Buxorov", "phone": "+998901234604"},
            {"first": "Farrux", "last": "Xorazmov", "phone": "+998901234605"},
            {"first": "Gulom", "last": "Navoiyov", "phone": "+998901234606"},
            {"first": "Hamid", "last": "Andijonov", "phone": "+998901234607"},
            {"first": "Ilhom", "last": "Fargonov", "phone": "+998901234608"},
            {"first": "Jamol", "last": "Qashqadaryov", "phone": "+998901234609"},
            {"first": "Karim", "last": "Surxondaryov", "phone": "+998901234610"},
            {"first": "Laziz", "last": "Namanganlik", "phone": "+998901234611"},
            {"first": "Mirzo", "last": "Jizzaxlik", "phone": "+998901234612"},
        ]

        customers = []
        for i in range(min(count, len(customer_data))):
            data = customer_data[i]
            username = f"customer{i + 1}"

            # Assign to company (distribute customers across companies)
            company = companies[i % len(companies)] if companies else None

            # Create user
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@company.com",
                    "first_name": data["first"],
                    "last_name": data["last"],
                    "user_type": "customer",
                    "is_staff": False,
                    "is_active": True,
                    # Legacy fields
                    "phone_number": data["phone"],
                    "bot_access": True,
                    "company": company,
                },
            )
            if created:
                user.set_password("customer123")
                user.save()

            # Create profile (company is REQUIRED for customers)
            if company:
                CustomerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "phone_number": data["phone"],
                        "bot_access": True,
                        "company": company,
                        "telegram_user_id": 200000000 + i,
                    },
                )
            customers.append(user)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(customers)} customers (customer1/customer123)"))
        return customers

    def _seed_containers(self, count):
        """Seed containers with realistic numbers"""
        self.stdout.write(f"Seeding {count} containers...")

        shipping_prefixes = ["MSKU", "TCLU", "GESU", "TEMU", "HLBU", "OOLU", "CMAU", "HDMU"]
        iso_types = ["22G1", "42G1", "45G1", "L5G1", "22R1", "42R1"]
        iso_weights = [25, 35, 20, 5, 10, 5]

        containers = []
        for i in range(count):
            prefix = random.choice(shipping_prefixes)
            number = f"{random.randint(1000000, 9999999):07d}"
            container_number = f"{prefix}{number}"

            try:
                container, _ = Container.objects.get_or_create(
                    container_number=container_number,
                    defaults={
                        "iso_type": random.choices(iso_types, weights=iso_weights)[0],
                    },
                )
                containers.append(container)
            except Exception:
                pass  # Skip duplicates

        self.stdout.write(self.style.SUCCESS(f"  Created {len(containers)} containers"))
        return containers

    def _seed_container_entries(self, count, containers, users, owners, companies):
        """Seed container entries with all relationships"""
        self.stdout.write(f"Seeding {count} container entries...")

        truck_plates = [
            "01A123BC",
            "01B456DE",
            "01C789FG",
            "01D012HI",
            "10E345JK",
            "10F678LM",
            "10G901NO",
            "10H234PQ",
        ]
        wagon_numbers = ["W123456", "W234567", "W345678", "W456789"]
        locations = ["Zone A-1", "Zone A-2", "Zone B-1", "Zone B-2", "Zone C-1", "Yard D"]
        cargo_names = ["Electronics", "Textiles", "Cotton", "Fruits", "Machinery", "Chemicals", ""]

        end_date = timezone.now()
        start_date = end_date - timedelta(days=60)

        entries = []
        for i in range(count):
            container = random.choice(containers)
            user = random.choice(users)

            # Random entry time
            random_seconds = random.randint(0, int((end_date - start_date).total_seconds()))
            entry_time = start_date + timedelta(seconds=random_seconds)

            # Transport
            transport_type = random.choice(["TRUCK", "WAGON", "TRAIN"])
            if transport_type == "TRUCK":
                transport_number = random.choice(truck_plates)
            elif transport_type == "WAGON":
                transport_number = random.choice(wagon_numbers)
            else:
                transport_number = f"T{random.randint(100, 999)}"

            # Status
            status = random.choices(["EMPTY", "LADEN"], weights=[60, 40])[0]

            # Exit info (30% have exited)
            exit_date = None
            exit_transport_type = None
            exit_transport_number = ""
            if random.random() < 0.3:
                exit_date = entry_time + timedelta(days=random.randint(1, 14))
                if exit_date > end_date:
                    exit_date = None
                else:
                    exit_transport_type = random.choice(["TRUCK", "WAGON", "TRAIN"])
                    exit_transport_number = random.choice(truck_plates)

            try:
                entry = ContainerEntry.objects.create(
                    container=container,
                    entry_time=entry_time,
                    status=status,
                    transport_type=transport_type,
                    transport_number=transport_number,
                    recorded_by=user,
                    container_owner=random.choice(owners) if owners and random.random() > 0.2 else None,
                    company=random.choice(companies) if companies and random.random() > 0.3 else None,
                    client_name=random.choice(["Client A", "Client B", "Client C", ""]),
                    cargo_name=random.choice(cargo_names) if status == "LADEN" else "",
                    cargo_weight=Decimal(str(round(random.uniform(5, 25), 2)))
                    if status == "LADEN" and random.random() > 0.5
                    else None,
                    location=random.choice(locations),
                    exit_date=exit_date,
                    exit_transport_type=exit_transport_type,
                    exit_transport_number=exit_transport_number,
                )
                entries.append(entry)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Entry creation failed: {e}"))

        self.stdout.write(self.style.SUCCESS(f"  Created {len(entries)} container entries"))
        return entries

    def _seed_crane_operations(self, entries):
        """Seed crane operations for some entries"""
        self.stdout.write("Seeding crane operations...")

        operations = []
        for entry in entries:
            # 40% of entries have crane operations
            if random.random() < 0.4:
                num_ops = random.randint(1, 3)
                for j in range(num_ops):
                    op_time = entry.entry_time + timedelta(hours=random.randint(1, 48))
                    if entry.exit_date and op_time > entry.exit_date:
                        continue

                    op = CraneOperation.objects.create(
                        container_entry=entry,
                        operation_date=op_time,
                    )
                    operations.append(op)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(operations)} crane operations"))

    def _seed_vehicle_entries(self, count, customers, managers, destinations):
        """Seed vehicle entries"""
        self.stdout.write(f"Seeding {count} vehicle entries...")

        plates = [
            "01A111AA",
            "01B222BB",
            "01C333CC",
            "01D444DD",
            "10E555EE",
            "10F666FF",
            "10G777GG",
            "10H888HH",
            "20I999II",
            "20J000JJ",
            "30K111KK",
            "40L222LL",
        ]

        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        entries = []
        for i in range(count):
            plate = random.choice(plates)
            entry_time = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))

            # Vehicle type
            vehicle_type = random.choices(["CARGO", "LIGHT"], weights=[70, 30])[0]

            # Status (most are ON_TERMINAL or EXITED)
            status = random.choices(["ON_TERMINAL", "EXITED", "WAITING"], weights=[40, 50, 10])[0]

            # Exit time for EXITED vehicles
            exit_time = None
            if status == "EXITED":
                exit_time = entry_time + timedelta(hours=random.randint(1, 24))
                if exit_time > end_date:
                    exit_time = end_date

            # Customer for pre-order related entries
            customer = None
            if status in ["WAITING", "ON_TERMINAL"] and random.random() < 0.3:
                customer = random.choice(customers) if customers else None

            try:
                entry = VehicleEntry.objects.create(
                    license_plate=plate + str(i),  # Make unique
                    entry_time=entry_time if status != "WAITING" else None,
                    status=status,
                    vehicle_type=vehicle_type,
                    customer=customer,
                    recorded_by=random.choice(managers) if managers and status != "WAITING" else None,
                    destination=random.choice(destinations) if destinations and vehicle_type == "CARGO" else None,
                    visitor_type=random.choice(["EMPLOYEE", "CLIENT", "GUEST"]) if vehicle_type == "LIGHT" else None,
                    transport_type=random.choice(["TRUCK", "PLATFORM", "TRAILER"]) if vehicle_type == "CARGO" else None,
                    entry_load_status=random.choice(["LOADED", "EMPTY"]) if vehicle_type == "CARGO" else None,
                    cargo_type=random.choice(["CONTAINER", "FOOD", "METAL", "OTHER"])
                    if vehicle_type == "CARGO"
                    else None,
                    exit_time=exit_time,
                    exit_load_status=random.choice(["LOADED", "EMPTY"])
                    if exit_time and vehicle_type == "CARGO"
                    else None,
                )
                entries.append(entry)
            except Exception:
                pass  # Skip constraint violations (unique plate on terminal)

        self.stdout.write(self.style.SUCCESS(f"  Created {len(entries)} vehicle entries"))
        return entries

    def _seed_preorders(self, count, customers, vehicle_entries, container_entries):
        """Seed pre-orders with relationships"""
        self.stdout.write(f"Seeding {count} pre-orders...")

        if not customers:
            self.stdout.write(self.style.WARNING("  Skipped (no customers)"))
            return

        plates = ["01A111AA", "01B222BB", "01C333CC", "01D444DD", "10E555EE"]

        preorders = []
        for i in range(count):
            customer = random.choice(customers)

            # Status distribution
            status = random.choices(["PENDING", "MATCHED", "COMPLETED", "CANCELLED"], weights=[30, 25, 35, 10])[0]

            # Timestamps based on status
            matched_at = None
            cancelled_at = None
            vehicle_entry = None
            matched_entry = None

            if status in ["MATCHED", "COMPLETED"]:
                matched_at = timezone.now() - timedelta(hours=random.randint(1, 72))
                if vehicle_entries:
                    vehicle_entry = random.choice(vehicle_entries)
                if status == "COMPLETED" and container_entries:
                    matched_entry = random.choice(container_entries)
            elif status == "CANCELLED":
                cancelled_at = timezone.now() - timedelta(hours=random.randint(1, 48))

            try:
                preorder = PreOrder.objects.create(
                    customer=customer,
                    plate_number=random.choice(plates) + str(random.randint(100, 999)),
                    operation_type=random.choice(["LOAD", "UNLOAD"]),
                    status=status,
                    vehicle_entry=vehicle_entry,
                    matched_entry=matched_entry,
                    matched_at=matched_at,
                    cancelled_at=cancelled_at,
                    notes=f"Test pre-order {i + 1}" if random.random() > 0.5 else "",
                    batch_id=uuid.uuid4() if random.random() > 0.7 else None,
                )
                preorders.append(preorder)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  PreOrder creation failed: {e}"))

        self.stdout.write(self.style.SUCCESS(f"  Created {len(preorders)} pre-orders"))

    def _print_summary(self):
        """Print summary of all seeded data"""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("  SEEDING COMPLETE - SUMMARY"))
        self.stdout.write("=" * 70)

        counts = [
            ("File Categories", FileCategory.objects.count()),
            ("Destinations", Destination.objects.count()),
            ("Container Owners", ContainerOwner.objects.count()),
            ("Companies", Company.objects.count()),
            ("Users (Total)", CustomUser.objects.count()),
            ("  - Admins", CustomUser.objects.filter(user_type="admin").count()),
            ("  - Managers", CustomUser.objects.filter(user_type="manager").count()),
            ("  - Customers", CustomUser.objects.filter(user_type="customer").count()),
            ("Manager Profiles", ManagerProfile.objects.count()),
            ("Customer Profiles", CustomerProfile.objects.count()),
            ("Containers", Container.objects.count()),
            ("Container Entries", ContainerEntry.objects.count()),
            ("Crane Operations", CraneOperation.objects.count()),
            ("Vehicle Entries", VehicleEntry.objects.count()),
            ("Pre-Orders", PreOrder.objects.count()),
        ]

        for name, count in counts:
            self.stdout.write(f"  {name:.<40} {count:>6}")

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("\n  Test Credentials:"))
        self.stdout.write("  Admin:    admin / admin123")
        self.stdout.write("  Manager:  manager1 / manager123")
        self.stdout.write("  Customer: customer1 / customer123")
        self.stdout.write("=" * 70 + "\n")
