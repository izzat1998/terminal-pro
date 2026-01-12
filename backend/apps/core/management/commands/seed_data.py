import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Company, CustomerProfile, ManagerProfile
from apps.containers.models import Container
from apps.containers.services import ContainerService
from apps.files.models import FileCategory
from apps.terminal_operations.models import (
    ContainerEntry,
    ContainerOwner,
    CraneOperation,
    PreOrder,
)
from apps.vehicles.models import Destination, VehicleEntry


User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with realistic, logically connected Uzbek test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--containers",
            type=int,
            default=50,
            help="Number of containers to create (default: 50)",
        )
        parser.add_argument(
            "--entries",
            type=int,
            default=100,
            help="Number of container entries to create (default: 100)",
        )
        parser.add_argument(
            "--vehicles",
            type=int,
            default=50,
            help="Number of vehicle entries to create (default: 50)",
        )
        parser.add_argument(
            "--preorders",
            type=int,
            default=20,
            help="Number of pre-orders to create (default: 20)",
        )
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            self._clear_data()

        # Create data in dependency order
        self.stdout.write(self.style.NOTICE("Starting database seeding..."))

        # 1. FileCategories (no dependencies)
        file_categories = self.create_file_categories()
        self.stdout.write(f"  Created {len(file_categories)} file categories")

        # 2. Companies (no dependencies)
        companies = self.create_companies()
        self.stdout.write(f"  Created {len(companies)} companies")

        # 3. ContainerOwners (no dependencies)
        container_owners = self.create_container_owners()
        self.stdout.write(f"  Created {len(container_owners)} container owners")

        # 4. Destinations (no dependencies)
        destinations = self.create_destinations()
        self.stdout.write(f"  Created {len(destinations)} destinations")

        # 5. Managers (depends on Companies)
        managers = self.create_managers(companies)
        self.stdout.write(f"  Created {len(managers)} managers with profiles")

        # 6. Customers (depends on Companies)
        customers = self.create_customers(companies)
        self.stdout.write(f"  Created {len(customers)} customers with profiles")

        # 7. Containers (no dependencies)
        container_service = ContainerService()
        containers = self.create_containers(container_service, options["containers"])
        self.stdout.write(f"  Created {len(containers)} containers")

        # 8. VehicleEntries (depends on Destinations, Customers, Managers)
        vehicle_entries = self.create_vehicle_entries(destinations, customers, managers, options["vehicles"])
        self.stdout.write(f"  Created {len(vehicle_entries)} vehicle entries")

        # 9. ContainerEntries (depends on Containers, Companies, ContainerOwners, Managers)
        container_entries = self.create_container_entries(
            containers, companies, container_owners, managers, options["entries"]
        )
        self.stdout.write(f"  Created {len(container_entries)} container entries")

        # 10. CraneOperations (depends on ContainerEntries)
        crane_operations = self.create_crane_operations(container_entries)
        self.stdout.write(f"  Created {len(crane_operations)} crane operations")

        # 11. PreOrders (depends on Customers, VehicleEntries, ContainerEntries)
        preorders = self.create_preorders(customers, vehicle_entries, container_entries, options["preorders"])
        self.stdout.write(f"  Created {len(preorders)} pre-orders")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully seeded database with:\n"
                f"  - {len(companies)} companies\n"
                f"  - {len(managers)} managers\n"
                f"  - {len(customers)} customers\n"
                f"  - {len(container_owners)} container owners\n"
                f"  - {len(destinations)} destinations\n"
                f"  - {len(containers)} containers\n"
                f"  - {len(container_entries)} container entries\n"
                f"  - {len(crane_operations)} crane operations\n"
                f"  - {len(vehicle_entries)} vehicle entries\n"
                f"  - {len(preorders)} pre-orders"
            )
        )

    def _clear_data(self):
        """Clear all seeded data (preserve superusers)"""
        PreOrder.objects.all().delete()
        CraneOperation.objects.all().delete()
        ContainerEntry.objects.all().delete()
        VehicleEntry.objects.all().delete()
        Container.objects.all().delete()
        ContainerOwner.objects.all().delete()
        Destination.objects.all().delete()
        CustomerProfile.objects.all().delete()
        ManagerProfile.objects.all().delete()
        Company.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        FileCategory.objects.all().delete()

    def create_file_categories(self):
        """Create file categories for uploads"""
        categories_data = [
            {
                "code": "container_image",
                "name": "Konteyner surati",
                "description": "Konteyner fotosurati",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                "max_file_size_mb": 5,
            },
            {
                "code": "vehicle_image",
                "name": "Avtomobil surati",
                "description": "Avtomobil fotosurati",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                "max_file_size_mb": 5,
            },
            {
                "code": "document",
                "name": "Hujjat",
                "description": "PDF hujjatlar",
                "allowed_mime_types": ["application/pdf"],
                "max_file_size_mb": 10,
            },
            {
                "code": "bill_of_lading",
                "name": "Yuk xati",
                "description": "Yuk hujjatlari",
                "allowed_mime_types": ["application/pdf", "image/jpeg", "image/png"],
                "max_file_size_mb": 10,
            },
        ]

        categories = []
        for data in categories_data:
            category, created = FileCategory.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "allowed_mime_types": data["allowed_mime_types"],
                    "max_file_size_mb": data["max_file_size_mb"],
                },
            )
            categories.append(category)
        return categories

    def create_companies(self):
        """Create Uzbek logistics companies"""
        companies_data = [
            {"name": "O'zbekiston Temir Yo'llari", "slug": "uzrailways"},
            {"name": "Toshkent Logistika", "slug": "tashkent-logistics"},
            {"name": "Ipak Yo'li Transport", "slug": "silk-road-transport"},
            {"name": "Navoiy Yuk Tashish", "slug": "navoi-freight"},
            {"name": "Buxoro Trans", "slug": "bukhara-trans"},
            {"name": "Samarqand Cargo", "slug": "samarkand-cargo"},
            {"name": "Farg'ona Logistics", "slug": "fergana-logistics"},
        ]

        companies = []
        for data in companies_data:
            company, created = Company.objects.get_or_create(
                slug=data["slug"],
                defaults={"name": data["name"], "is_active": True},
            )
            companies.append(company)
        return companies

    def create_container_owners(self):
        """Create container owner/shipping line companies"""
        owners_data = [
            {"name": "Maersk Line", "slug": "maersk"},
            {"name": "MSC - Mediterranean Shipping", "slug": "msc"},
            {"name": "CMA CGM", "slug": "cma-cgm"},
            {"name": "Hapag-Lloyd", "slug": "hapag-lloyd"},
            {"name": "OOCL", "slug": "oocl"},
            {"name": "Evergreen", "slug": "evergreen"},
            {"name": "COSCO Shipping", "slug": "cosco"},
        ]

        owners = []
        for data in owners_data:
            owner, created = ContainerOwner.objects.get_or_create(
                slug=data["slug"],
                defaults={"name": data["name"]},
            )
            owners.append(owner)
        return owners

    def create_destinations(self):
        """Create terminal destinations/zones"""
        destinations_data = [
            {"name": "Konteyner Maydoni K1", "code": "konteyner-k1", "zone": "K1"},
            {"name": "Konteyner Maydoni K2", "code": "konteyner-k2", "zone": "K2"},
            {"name": "Konteyner Maydoni K3", "code": "konteyner-k3", "zone": "K3"},
            {"name": "Ombor H1", "code": "ombor-h1", "zone": "H1"},
            {"name": "Ombor H2", "code": "ombor-h2", "zone": "H2"},
            {"name": "Yuklash Joyi L1", "code": "yuklash-l1", "zone": "L1"},
            {"name": "Yuklash Joyi L2", "code": "yuklash-l2", "zone": "L2"},
            {"name": "Bojxona Hududi C1", "code": "bojxona-c1", "zone": "C1"},
        ]

        destinations = []
        for data in destinations_data:
            destination, created = Destination.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "zone": data["zone"],
                    "is_active": True,
                },
            )
            destinations.append(destination)
        return destinations

    def create_managers(self, companies):
        """Create manager users with ManagerProfile"""
        managers_data = [
            {
                "first_name": "Aziz",
                "last_name": "Karimov",
                "phone": "+998901234567",
                "username": "aziz_manager",
            },
            {
                "first_name": "Bobur",
                "last_name": "Toshmatov",
                "phone": "+998902345678",
                "username": "bobur_manager",
            },
            {
                "first_name": "Dilshod",
                "last_name": "Normatov",
                "phone": "+998903456789",
                "username": "dilshod_manager",
            },
            {
                "first_name": "Eldor",
                "last_name": "Saidov",
                "phone": "+998904567890",
                "username": "eldor_manager",
            },
            {
                "first_name": "Farrux",
                "last_name": "Alimov",
                "phone": "+998905678901",
                "username": "farrux_manager",
            },
        ]

        managers = []
        for i, data in enumerate(managers_data):
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "user_type": "manager",
                    "is_staff": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password("manager123")
                user.save()

            # Create ManagerProfile
            profile, _ = ManagerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": data["phone"],
                    "bot_access": True,
                    "gate_access": True,
                    "language": random.choice(["ru", "uz"]),
                    "company": random.choice(companies) if companies else None,
                },
            )
            managers.append(user)
        return managers

    def create_customers(self, companies):
        """Create customer users with CustomerProfile"""
        customers_data = [
            {
                "first_name": "Jamshid",
                "last_name": "Rahimov",
                "phone": "+998911234567",
                "username": "jamshid_customer",
            },
            {
                "first_name": "Kamol",
                "last_name": "Umarov",
                "phone": "+998912345678",
                "username": "kamol_customer",
            },
            {
                "first_name": "Laziz",
                "last_name": "Tursunov",
                "phone": "+998913456789",
                "username": "laziz_customer",
            },
            {
                "first_name": "Mansur",
                "last_name": "Qodirov",
                "phone": "+998914567890",
                "username": "mansur_customer",
            },
            {
                "first_name": "Nodir",
                "last_name": "Xolmatov",
                "phone": "+998915678901",
                "username": "nodir_customer",
            },
        ]

        customers = []
        for i, data in enumerate(customers_data):
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "user_type": "customer",
                    "is_active": True,
                },
            )
            if created:
                user.set_password("customer123")
                user.save()

            # Create CustomerProfile - each customer linked to a company
            company = companies[i % len(companies)] if companies else None
            profile, _ = CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": data["phone"],
                    "bot_access": True,
                    "language": random.choice(["ru", "uz"]),
                    "company": company,
                },
            )
            customers.append(user)
        return customers

    def create_containers(self, container_service, count):
        """Create containers with realistic ISO numbers"""
        containers = []

        # Real shipping line prefixes
        shipping_lines = [
            "MSKU",  # Maersk
            "MSCU",  # MSC
            "CMAU",  # CMA CGM
            "HLCU",  # Hapag-Lloyd
            "OOLU",  # OOCL
            "EGLV",  # Evergreen
            "COSU",  # COSCO
            "TCLU",  # Textainer
            "GESU",  # GE Seaco
        ]

        # ISO 6346 type codes with weighted distribution
        iso_types = ["22G1", "42G1", "45G1", "L5G1", "22R1", "42R1", "45R1"]
        iso_weights = [25, 35, 20, 5, 5, 7, 3]  # Most common are GP containers

        for i in range(count):
            prefix = random.choice(shipping_lines)
            number = f"{random.randint(1000000, 9999999):07d}"
            container_number = f"{prefix}{number}"

            try:
                container = container_service.get_or_create_container(
                    container_number=container_number,
                    iso_type=random.choices(iso_types, weights=iso_weights)[0],
                )
                containers.append(container)
            except Exception as e:
                self.stdout.write(f"    Error creating container: {e}")

        return containers

    def create_vehicle_entries(self, destinations, customers, managers, count):
        """Create vehicle entries with proper relationships"""
        entries = []

        # Uzbek region codes for license plates
        region_codes = ["01", "10", "20", "30", "40", "50", "60", "70", "80", "90"]

        # Generate entries over the last 7 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)

        for i in range(count):
            # Generate Uzbek-style license plate
            region = random.choice(region_codes)
            letter1 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            numbers = f"{random.randint(100, 999)}"
            letter2 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            letter3 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            license_plate = f"{region}{letter1}{numbers}{letter2}{letter3}"

            # Random entry time
            random_time = start_date + timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )

            # Status distribution
            status = random.choices(
                ["ON_TERMINAL", "EXITED", "WAITING"],
                weights=[40, 50, 10],
            )[0]

            # Vehicle type distribution
            vehicle_type = random.choices(
                ["CARGO", "LIGHT"],
                weights=[70, 30],
            )[0]

            entry_data = {
                "license_plate": license_plate,
                "status": status,
                "vehicle_type": vehicle_type,
                "destination": random.choice(destinations) if destinations else None,
                "recorded_by": random.choice(managers) if managers else None,
            }

            # Set entry time for ON_TERMINAL and EXITED
            if status in ["ON_TERMINAL", "EXITED"]:
                entry_data["entry_time"] = random_time

            # Set exit time for EXITED vehicles
            if status == "EXITED":
                exit_time = random_time + timedelta(hours=random.randint(1, 48))
                entry_data["exit_time"] = min(exit_time, end_date)

            # Add cargo-specific fields
            if vehicle_type == "CARGO":
                entry_data["transport_type"] = random.choice(["TRUCK", "PLATFORM", "TRAILER", "MINI_TRUCK", "GAZELLE"])
                entry_data["entry_load_status"] = random.choice(["LOADED", "EMPTY"])
                if entry_data["entry_load_status"] == "LOADED":
                    entry_data["cargo_type"] = random.choice(
                        ["CONTAINER", "FOOD", "METAL", "WOOD", "EQUIPMENT", "OTHER"]
                    )
            else:
                entry_data["visitor_type"] = random.choice(["EMPLOYEE", "CLIENT", "GUEST"])

            # Link some entries to customers
            if random.random() < 0.3 and customers:
                entry_data["customer"] = random.choice(customers)

            try:
                entry = VehicleEntry.objects.create(**entry_data)
                entries.append(entry)
            except Exception as e:
                self.stdout.write(f"    Error creating vehicle entry: {e}")

        return entries

    def create_container_entries(self, containers, companies, container_owners, managers, count):
        """Create container entries with full relationships"""
        entries = []

        # Uzbek cargo names
        cargo_names = [
            "Paxta (Cotton)",
            "Meva-sabzavot",
            "Qurilish materiallari",
            "Tekstil mahsulotlari",
            "Elektronika",
            "Oziq-ovqat mahsulotlari",
            "Kimyoviy moddalar",
            "Mashinasozlik uskunalari",
            "Mebel",
            "Avtomobil ehtiyot qismlari",
        ]

        # Client names
        client_names = [
            "Toshkent Savdo",
            "Navoiy Mining",
            "Buxoro Textile",
            "Samarqand Trade",
            "Farg'ona Agro",
            "Andijon Export",
            "Namangan Import",
            "Qo'qon Logistics",
        ]

        # Uzbek license plates for trucks
        truck_plates = [
            f"{random.choice(['01', '10', '20', '30'])}{random.choice('ABCD')}{random.randint(100, 999)}{random.choice('EF')}{random.choice('GH')}"
            for _ in range(20)
        ]

        wagon_numbers = [f"W{random.randint(100000, 999999)}" for _ in range(10)]
        train_numbers = [f"T{random.randint(1000, 9999)}" for _ in range(5)]

        # Location codes on terminal
        locations = ["K1-A01", "K1-B02", "K2-C03", "K2-D04", "H1-E05", "L1-F06"]

        # Destination stations
        stations = [
            "Toshkent-Tovarniy",
            "Chukursay",
            "Sergeli",
            "Bekabad",
            "Guliston",
            "Jizzax",
        ]

        # Generate entries over the last 30 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        for i in range(count):
            if not containers:
                break

            container = random.choice(containers)

            # Random entry time
            random_time = start_date + timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )

            # Status distribution
            status = random.choices(
                ["EMPTY", "LADEN"],
                weights=[70, 30],
            )[0]

            # Transport type distribution
            transport_type = random.choices(
                ["TRUCK", "WAGON", "TRAIN"],
                weights=[60, 30, 10],
            )[0]

            # Select transport number based on type
            if transport_type == "TRUCK":
                transport_number = random.choice(truck_plates)
            elif transport_type == "WAGON":
                transport_number = random.choice(wagon_numbers)
            else:
                transport_number = random.choice(train_numbers)

            entry_data = {
                "container": container,
                "entry_time": random_time,
                "status": status,
                "transport_type": transport_type,
                "transport_number": transport_number,
                "recorded_by": random.choice(managers) if managers else None,
                "container_owner": (random.choice(container_owners) if container_owners else None),
                "company": random.choice(companies) if companies else None,
                "client_name": random.choice(client_names),
                "location": random.choice(locations),
            }

            # Add cargo details for LADEN containers
            if status == "LADEN":
                entry_data["cargo_name"] = random.choice(cargo_names)
                entry_data["cargo_weight"] = Decimal(str(round(random.uniform(5, 25), 2)))

            # Add train number for TRAIN transport
            if transport_type == "TRAIN":
                entry_data["entry_train_number"] = transport_number

            # 30% of entries have exited
            if random.random() < 0.3:
                exit_time = random_time + timedelta(days=random.randint(1, 15))
                if exit_time <= end_date:
                    entry_data["exit_date"] = exit_time
                    entry_data["exit_transport_type"] = random.choice(["TRUCK", "WAGON", "TRAIN"])
                    entry_data["exit_transport_number"] = random.choice(truck_plates + wagon_numbers)
                    entry_data["destination_station"] = random.choice(stations)
                    if entry_data["exit_transport_type"] == "TRAIN":
                        entry_data["exit_train_number"] = random.choice(train_numbers)

            try:
                entry = ContainerEntry.objects.create(**entry_data)
                # Update timestamps for realism
                entry.created_at = random_time
                entry.updated_at = random_time
                entry.save(update_fields=["created_at", "updated_at"])
                entries.append(entry)
            except Exception as e:
                self.stdout.write(f"    Error creating container entry: {e}")

        return entries

    def create_crane_operations(self, container_entries):
        """Create crane operations for container entries"""
        operations = []

        for entry in container_entries:
            # 1-3 crane operations per entry
            num_operations = random.randint(1, 3)

            for i in range(num_operations):
                # Operation happens after entry time
                op_time = entry.entry_time + timedelta(hours=random.randint(1, 24 * (i + 1)))

                try:
                    operation = CraneOperation.objects.create(
                        container_entry=entry,
                        operation_date=op_time,
                    )
                    operations.append(operation)
                except Exception as e:
                    self.stdout.write(f"    Error creating crane operation: {e}")

        return operations

    def create_preorders(self, customers, vehicle_entries, container_entries, count):
        """Create pre-orders with proper status flow"""
        preorders = []

        if not customers:
            return preorders

        # Filter vehicle entries that can be linked
        linkable_vehicles = [v for v in vehicle_entries if v.status in ["ON_TERMINAL", "EXITED"]]
        # Filter container entries that can be linked
        linkable_entries = [e for e in container_entries if e.exit_date is not None]

        region_codes = ["01", "10", "20", "30", "40"]

        for i in range(count):
            customer = random.choice(customers)

            # Generate plate number
            region = random.choice(region_codes)
            letter1 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            numbers = f"{random.randint(100, 999)}"
            letter2 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            letter3 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            plate_number = f"{region}{letter1}{numbers}{letter2}{letter3}"

            # Status distribution
            status = random.choices(
                ["PENDING", "MATCHED", "COMPLETED", "CANCELLED"],
                weights=[30, 40, 20, 10],
            )[0]

            preorder_data = {
                "customer": customer,
                "plate_number": plate_number,
                "operation_type": random.choice(["LOAD", "UNLOAD"]),
                "status": status,
                "notes": random.choice(
                    [
                        "",
                        "Tezkor yetkazib berish",
                        "Maxsus yuk",
                        "Ehtiyotkorlik bilan",
                    ]
                ),
            }

            # Add matched_at for MATCHED/COMPLETED
            if status in ["MATCHED", "COMPLETED"]:
                preorder_data["matched_at"] = timezone.now() - timedelta(hours=random.randint(1, 48))
                # Link to vehicle entry
                if linkable_vehicles:
                    preorder_data["vehicle_entry"] = random.choice(linkable_vehicles)

            # Add container entry for COMPLETED
            if status == "COMPLETED" and linkable_entries:
                preorder_data["matched_entry"] = random.choice(linkable_entries)

            # Add cancelled_at for CANCELLED
            if status == "CANCELLED":
                preorder_data["cancelled_at"] = timezone.now() - timedelta(hours=random.randint(1, 24))

            try:
                preorder = PreOrder.objects.create(**preorder_data)
                preorders.append(preorder)
            except Exception as e:
                self.stdout.write(f"    Error creating pre-order: {e}")

        return preorders
