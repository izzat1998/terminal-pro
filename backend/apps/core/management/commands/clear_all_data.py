"""
Clear all data except the main admin user (admin/admin123).

This command removes:
- All operational data (entries, work orders, positions, pre-orders, containers)
- All foundation data (companies, managers, customers, vehicles, tariffs, owners)
- All admin users EXCEPT the one specified (default: username='admin')

Preserves:
- The main admin user (default: username='admin', password='admin123')

Usage:
    python manage.py clear_all_data                    # Clear all except admin/admin123
    python manage.py clear_all_data --admin-username system  # Preserve different admin
    python manage.py clear_all_data --yes              # Skip confirmation
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

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
    help = "Clear all data except the main admin user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-username",
            type=str,
            default="admin",
            help="Username of admin to preserve (default: admin)",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        admin_username = options["admin_username"]
        skip_confirmation = options["yes"]

        self.stdout.write(self.style.WARNING("\n⚠️  DATABASE CLEANUP\n"))
        self.stdout.write("This will delete:")
        self.stdout.write("  • All operational data (entries, work orders, positions)")
        self.stdout.write("  • All foundation data (companies, users, vehicles, tariffs)")
        self.stdout.write(f"\nPreserving:")
        self.stdout.write(f"  ✓ Admin user: {admin_username}\n")

        # Check if admin exists
        admin_user = User.objects.filter(
            username=admin_username, user_type="admin", is_active=True
        ).first()

        if not admin_user:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Admin user '{admin_username}' not found. Will be created with password 'admin123'.\n"
                )
            )

        if not skip_confirmation:
            confirm = input("Type 'yes' to continue: ")
            if confirm.lower() != "yes":
                self.stdout.write(self.style.ERROR("Aborted.\n"))
                return

        try:
            with transaction.atomic():
                stats = self._clear_all_data(admin_username, admin_user)

            # Summary
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
            self.stdout.write(self.style.SUCCESS("✅ DATABASE CLEARED"))
            self.stdout.write(self.style.SUCCESS("=" * 70))
            self.stdout.write(f"\n  Operational data cleared: {stats['operational']} records")
            self.stdout.write(f"  Foundation data cleared: {stats['foundation']} records")
            self.stdout.write(f"  Admin users removed: {stats['admins_removed']}")
            self.stdout.write(f"\n  Preserved: {admin_username} (admin)")
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
            self.stdout.write("\nReady for fresh data generation!")
            self.stdout.write("Next steps:")
            self.stdout.write("  1. python manage.py generate_foundation_data")
            self.stdout.write("  2. python manage.py generate_realistic_data_v2")
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 70 + "\n"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}\n"))
            raise

    def _clear_all_data(self, admin_username: str, admin_user) -> dict:
        """Clear all data except specified admin"""
        stats = {"operational": 0, "foundation": 0, "admins_removed": 0}

        # Phase 1: Clear operational data
        self.stdout.write("\n🗑️  Phase 1: Clearing operational data...")

        stats["operational"] += WorkOrder.objects.count()
        WorkOrder.objects.all().delete()

        stats["operational"] += ContainerPosition.objects.count()
        ContainerPosition.objects.all().delete()

        stats["operational"] += PreOrder.objects.count()
        PreOrder.objects.all().delete()

        stats["operational"] += ContainerEntry.objects.count()
        ContainerEntry.objects.all().delete()

        stats["operational"] += Container.objects.count()
        Container.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f"  ✓ Cleared {stats['operational']} operational records"))

        # Phase 2: Clear foundation data
        self.stdout.write("\n🗑️  Phase 2: Clearing foundation data...")

        stats["foundation"] += TerminalVehicle.objects.count()
        TerminalVehicle.objects.all().delete()

        stats["foundation"] += TariffRate.objects.count()
        TariffRate.objects.all().delete()

        stats["foundation"] += Tariff.objects.count()
        Tariff.objects.all().delete()

        stats["foundation"] += ContainerOwner.objects.count()
        ContainerOwner.objects.all().delete()

        stats["foundation"] += ManagerProfile.objects.count()
        ManagerProfile.objects.all().delete()

        stats["foundation"] += CustomerProfile.objects.count()
        CustomerProfile.objects.all().delete()

        # Remove managers and customers
        manager_count = User.objects.filter(user_type="manager").count()
        User.objects.filter(user_type="manager").delete()
        stats["foundation"] += manager_count

        customer_count = User.objects.filter(user_type="customer").count()
        User.objects.filter(user_type="customer").delete()
        stats["foundation"] += customer_count

        stats["foundation"] += Company.objects.count()
        Company.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f"  ✓ Cleared {stats['foundation']} foundation records"))

        # Phase 3: Clear other admins (except the one we want to keep)
        self.stdout.write("\n🗑️  Phase 3: Clearing other admin users...")

        other_admins = User.objects.filter(user_type="admin").exclude(username=admin_username)
        stats["admins_removed"] = other_admins.count()
        other_admins.delete()

        self.stdout.write(self.style.SUCCESS(f"  ✓ Removed {stats['admins_removed']} other admin users"))

        # Phase 4: Ensure admin user exists with correct password
        if not admin_user:
            self.stdout.write(f"\n🔧 Creating admin user: {admin_username}...")
            admin_user = User.objects.create_user(
                username=admin_username,
                password="admin123",
                user_type="admin",
                first_name="Admin",
                last_name="User",
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created admin: {admin_username}"))
        else:
            # Reset password to admin123
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"  ✓ Password reset to 'admin123' for {admin_username}"))

        return stats
