"""
Management command to create ManagerProfile/CustomerProfile records
for existing users who don't have them.

Usage:
    python manage.py populate_profiles          # Dry run (shows what would be created)
    python manage.py populate_profiles --apply  # Actually create the profiles
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import CustomerProfile, CustomUser, ManagerProfile


class Command(BaseCommand):
    help = 'Create ManagerProfile/CustomerProfile for existing users without profiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually create the profiles (default is dry run)',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN - use --apply to create profiles\n'))

        self.populate_manager_profiles(apply)
        self.stdout.write('')
        self.populate_customer_profiles(apply)

    def populate_manager_profiles(self, apply):
        """Create ManagerProfile records for existing managers."""
        self.stdout.write(self.style.HTTP_INFO('=== Manager Profiles ==='))

        # Find all managers
        all_managers = CustomUser.objects.filter(user_type='manager', is_active=True)
        self.stdout.write(f'Total active managers: {all_managers.count()}')

        # Find managers without profiles
        managers_without_profiles = []
        for manager in all_managers:
            try:
                _ = manager.manager_profile
            except ManagerProfile.DoesNotExist:
                managers_without_profiles.append(manager)

        self.stdout.write(f'Managers WITHOUT profile: {len(managers_without_profiles)}')

        if not managers_without_profiles:
            self.stdout.write(self.style.SUCCESS('All managers have profiles!'))
            return

        created = 0
        skipped = 0

        for manager in managers_without_profiles:
            # Validate required fields
            if not manager.phone_number:
                self.stdout.write(
                    self.style.WARNING(f'  SKIP: Manager {manager.id} ({manager.first_name}) - no phone')
                )
                skipped += 1
                continue

            # Check for duplicate phone
            if ManagerProfile.objects.filter(phone_number=manager.phone_number).exists():
                self.stdout.write(
                    self.style.WARNING(f'  SKIP: Manager {manager.id} - phone already in use')
                )
                skipped += 1
                continue

            if apply:
                with transaction.atomic():
                    ManagerProfile.objects.create(
                        user=manager,
                        phone_number=manager.phone_number,
                        telegram_user_id=manager.telegram_user_id,
                        telegram_username=manager.telegram_username or '',
                        bot_access=manager.bot_access,
                        gate_access=manager.gate_access,
                        language=manager.language or 'ru',
                        company=manager.company,
                    )
                self.stdout.write(
                    self.style.SUCCESS(f'  CREATED: {manager.first_name} ({manager.phone_number})')
                )
            else:
                self.stdout.write(
                    f'  WOULD CREATE: {manager.first_name} ({manager.phone_number})'
                )
            created += 1

        self.stdout.write(f'\nManager profiles: {created} created, {skipped} skipped')

    def populate_customer_profiles(self, apply):
        """Create CustomerProfile records for existing customers."""
        self.stdout.write(self.style.HTTP_INFO('=== Customer Profiles ==='))

        # Find all customers
        all_customers = CustomUser.objects.filter(user_type='customer', is_active=True)
        self.stdout.write(f'Total active customers: {all_customers.count()}')

        # Find customers without profiles
        customers_without_profiles = []
        for customer in all_customers:
            try:
                _ = customer.customer_profile
            except CustomerProfile.DoesNotExist:
                customers_without_profiles.append(customer)

        self.stdout.write(f'Customers WITHOUT profile: {len(customers_without_profiles)}')

        if not customers_without_profiles:
            self.stdout.write(self.style.SUCCESS('All customers have profiles!'))
            return

        created = 0
        skipped = 0

        for customer in customers_without_profiles:
            # Validate required fields
            if not customer.phone_number:
                self.stdout.write(
                    self.style.WARNING(f'  SKIP: Customer {customer.id} ({customer.first_name}) - no phone')
                )
                skipped += 1
                continue

            if not customer.company:
                self.stdout.write(
                    self.style.WARNING(f'  SKIP: Customer {customer.id} ({customer.first_name}) - no company')
                )
                skipped += 1
                continue

            # Check for duplicate phone
            if CustomerProfile.objects.filter(phone_number=customer.phone_number).exists():
                self.stdout.write(
                    self.style.WARNING(f'  SKIP: Customer {customer.id} - phone already in use')
                )
                skipped += 1
                continue

            if apply:
                with transaction.atomic():
                    CustomerProfile.objects.create(
                        user=customer,
                        phone_number=customer.phone_number,
                        telegram_user_id=customer.telegram_user_id,
                        telegram_username=customer.telegram_username or '',
                        bot_access=customer.bot_access,
                        language=customer.language or 'ru',
                        company=customer.company,
                    )
                self.stdout.write(
                    self.style.SUCCESS(f'  CREATED: {customer.first_name} ({customer.phone_number})')
                )
            else:
                self.stdout.write(
                    f'  WOULD CREATE: {customer.first_name} ({customer.phone_number})'
                )
            created += 1

        self.stdout.write(f'\nCustomer profiles: {created} created, {skipped} skipped')
