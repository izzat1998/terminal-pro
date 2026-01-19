"""
Generate foundation data (companies, users, vehicles, tariffs) - run once before operational data.

This command creates all static foundation data that operational data generation depends on:
- Admin users (system, controlroom)
- Companies with size classification (large, medium, small)
- Managers with profiles
- Customers with profiles
- Container owners
- Terminal vehicles
- Tariffs covering full period

Usage:
    python manage.py generate_foundation_data                    # Create all foundation data
    python manage.py generate_foundation_data --clear            # Clear and recreate
    python manage.py generate_foundation_data --companies-only   # Only create companies
"""

import random
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Company, CustomerProfile, ManagerProfile
from apps.billing.models import Tariff, TariffRate
from apps.terminal_operations.models import ContainerOwner, TerminalVehicle

User = get_user_model()


class Command(BaseCommand):
    help = "Generate foundation data (companies, users, vehicles, tariffs)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing foundation data before generation",
        )
        parser.add_argument(
            "--companies-only",
            action="store_true",
            help="Only create companies (skip users, vehicles, tariffs)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed progress information",
        )

    def handle(self, *args, **options):
        self.verbosity = 2 if options["verbose"] else 1
        companies_only = options["companies_only"]

        self.stdout.write(
            self.style.NOTICE("🏗️  Starting foundation data generation...\n")
        )

        if options["clear"]:
            self._clear_foundation_data(companies_only)

        try:
            with transaction.atomic():
                # Phase 1: Admin users
                if not companies_only:
                    self._log_phase("Phase 1: Creating admin users")
                    self._create_admin_users()

                # Phase 2: Companies
                self._log_phase("Phase 2: Creating companies")
                companies, company_sizes = self._create_companies()

                if companies_only:
                    self.stdout.write(self.style.SUCCESS("\n✅ Companies created successfully\n"))
                    return

                # Phase 3: Managers
                self._log_phase("Phase 3: Creating managers")
                self._create_managers()

                # Phase 4: Customers
                self._log_phase("Phase 4: Creating customers")
                self._create_customers(companies)

                # Phase 5: Container owners
                self._log_phase("Phase 5: Creating container owners")
                self._create_container_owners()

                # Phase 6: Terminal vehicles
                self._log_phase("Phase 6: Creating terminal vehicles")
                self._create_terminal_vehicles()

                # Phase 7: Tariffs
                self._log_phase("Phase 7: Creating tariffs")
                self._create_tariffs(companies)

            self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
            self.stdout.write(self.style.SUCCESS("✅ FOUNDATION DATA CREATED"))
            self.stdout.write(self.style.SUCCESS("=" * 70))
            self.stdout.write("\nYou can now run: python manage.py generate_realistic_data_v2")
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 70 + "\n"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}\n"))
            raise

    def _clear_foundation_data(self, companies_only: bool):
        """Clear foundation data (requires operational data to be cleared first)"""
        self.stdout.write("🗑️  Clearing existing foundation data...")

        # First check if operational data exists
        from apps.terminal_operations.models import ContainerEntry, WorkOrder, ContainerPosition, PreOrder
        from apps.containers.models import Container

        operational_count = (
            ContainerEntry.objects.count()
            + WorkOrder.objects.count()
            + ContainerPosition.objects.count()
            + PreOrder.objects.count()
            + Container.objects.count()
        )

        if operational_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Found {operational_count} operational records. Clearing them first...\n"
                )
            )
            WorkOrder.objects.all().delete()
            ContainerPosition.objects.all().delete()
            PreOrder.objects.all().delete()
            ContainerEntry.objects.all().delete()
            Container.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  ✓ Operational data cleared\n"))

        if companies_only:
            Company.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  ✓ Companies cleared\n"))
            return

        # Clear in dependency order
        TerminalVehicle.objects.all().delete()
        TariffRate.objects.all().delete()
        Tariff.objects.all().delete()
        ContainerOwner.objects.all().delete()
        ManagerProfile.objects.all().delete()
        CustomerProfile.objects.all().delete()
        User.objects.filter(user_type__in=["manager", "customer"]).delete()
        Company.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("  ✓ Foundation data cleared\n"))

    def _create_admin_users(self):
        """Create admin users"""
        admins = [
            {"username": "system", "first_name": "System", "last_name": "Administrator"},
            {"username": "controlroom", "first_name": "Control", "last_name": "Room"},
        ]

        for data in admins:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "user_type": "admin",
                    "is_staff": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password("admin123")
                user.save()

        self._log_item(f"Created {len(admins)} admin users")

    def _create_companies(self) -> tuple[List[Company], Dict[int, str]]:
        """Create companies with size classification"""
        companies_data = [
            {"name": "O'zbekiston Temir Yo'llari", "slug": "uzrailways", "size": "large"},
            {"name": "Toshkent Logistika", "slug": "tashkent-logistics", "size": "large"},
            {"name": "Ipak Yo'li Transport", "slug": "silk-road-transport", "size": "medium"},
            {"name": "Navoiy Yuk Tashish", "slug": "navoi-freight", "size": "medium"},
            {"name": "Buxoro Trans", "slug": "bukhara-trans", "size": "small"},
            {"name": "Samarqand Cargo", "slug": "samarkand-cargo", "size": "small"},
            {"name": "Farg'ona Logistics", "slug": "fergana-logistics", "size": "small"},
        ]

        companies = []
        company_sizes = {}
        for data in companies_data:
            company, _ = Company.objects.get_or_create(
                slug=data["slug"],
                defaults={"name": data["name"], "is_active": True},
            )
            companies.append(company)
            company_sizes[company.id] = data["size"]

        self._log_item(f"Created {len(companies)} companies")
        return companies, company_sizes

    def _create_managers(self):
        """Create manager users with profiles"""
        managers_data = [
            {"first_name": "Aziz", "last_name": "Karimov", "phone": "+998901234567"},
            {"first_name": "Bobur", "last_name": "Toshmatov", "phone": "+998902345678"},
            {"first_name": "Sardor", "last_name": "Normatov", "phone": "+998903456789"},
            {"first_name": "Dilshod", "last_name": "Saidov", "phone": "+998904567890"},
        ]

        for data in managers_data:
            user, created = User.objects.get_or_create(
                username=f"{data['first_name'].lower()}_manager",
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "user_type": "manager",
                    "is_active": True,
                },
            )
            if created:
                user.set_password("manager123")
                user.save()

            ManagerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": data["phone"],
                    "telegram_user_id": random.randint(100000000, 999999999),
                    "bot_access": True,
                    "gate_access": True,
                    "language": "ru",
                },
            )

        self._log_item(f"Created {len(managers_data)} managers")

    def _create_customers(self, companies: List[Company]):
        """Create customer users with profiles"""
        customers_data = [
            {"first_name": "Jamshid", "last_name": "Rahimov", "phone": "+998911234567"},
            {"first_name": "Kamol", "last_name": "Umarov", "phone": "+998912345678"},
            {"first_name": "Laziz", "last_name": "Tursunov", "phone": "+998913456789"},
        ]

        for i, data in enumerate(customers_data):
            user, created = User.objects.get_or_create(
                username=f"{data['first_name'].lower()}_customer",
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

            company = companies[i % len(companies)]
            CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": data["phone"],
                    "telegram_user_id": random.randint(100000000, 999999999),
                    "bot_access": True,
                    "language": "ru",
                    "company": company,
                },
            )

        self._log_item(f"Created {len(customers_data)} customers")

    def _create_container_owners(self):
        """Create container owners"""
        owners_data = [
            {"name": "Maersk Line", "slug": "maersk", "prefix": "MSKU"},
            {"name": "MSC - Mediterranean Shipping", "slug": "msc", "prefix": "MSCU"},
            {"name": "CMA CGM", "slug": "cma-cgm", "prefix": "CMAU"},
            {"name": "Hapag-Lloyd", "slug": "hapag-lloyd", "prefix": "HLCU"},
            {"name": "COSCO Shipping", "slug": "cosco", "prefix": "COSU"},
        ]

        for data in owners_data:
            ContainerOwner.objects.get_or_create(
                slug=data["slug"],
                defaults={"name": data["name"]},
            )

        self._log_item(f"Created {len(owners_data)} container owners")

    def _create_terminal_vehicles(self):
        """Create terminal vehicles"""
        managers = list(User.objects.filter(user_type="manager", is_active=True))
        if not managers:
            self.stdout.write(self.style.WARNING("  ⚠️  No managers found, skipping vehicles"))
            return

        vehicles_data = [
            {"name": "RS-01", "operator_idx": 0},
            {"name": "RS-02", "operator_idx": 1},
            {"name": "RS-03", "operator_idx": 2},
        ]

        for data in vehicles_data:
            operator = managers[data["operator_idx"] % len(managers)]
            TerminalVehicle.objects.get_or_create(
                name=data["name"],
                defaults={
                    "vehicle_type": "REACH_STACKER",
                    "is_active": True,
                    "operator": operator,
                },
            )

        self._log_item(f"Created {len(vehicles_data)} terminal vehicles")

    def _create_tariffs(self, companies: List[Company]):
        """Create tariffs covering the full period"""
        start_date = timezone.now().date() - timedelta(days=100)

        system_admin = User.objects.filter(user_type="admin", username="system").first()
        if not system_admin:
            system_admin = User.objects.filter(user_type="admin").first()

        if not system_admin:
            self.stdout.write(self.style.WARNING("  ⚠️  No admin found, skipping tariffs"))
            return

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

    def _log_phase(self, message: str):
        """Log phase header"""
        self.stdout.write(self.style.NOTICE(f"\n{message}"))

    def _log_item(self, message: str):
        """Log individual item"""
        if self.verbosity >= 1:
            self.stdout.write(f"  ✓ {message}")
