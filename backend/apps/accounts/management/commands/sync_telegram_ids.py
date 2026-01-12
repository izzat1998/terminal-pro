"""
Management command to sync telegram_user_id from CustomUser to ManagerProfile/CustomerProfile.

This handles cases where profiles exist but telegram_user_id wasn't copied from the legacy field.

Usage:
    python manage.py sync_telegram_ids          # Dry run (shows what would be updated)
    python manage.py sync_telegram_ids --apply  # Actually update the profiles
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import CustomerProfile, ManagerProfile


class Command(BaseCommand):
    help = 'Sync telegram_user_id from CustomUser legacy field to Profile models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually update the profiles (default is dry run)',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN - use --apply to update profiles\n'))

        self.sync_manager_telegram_ids(apply)
        self.stdout.write('')
        self.sync_customer_telegram_ids(apply)

    def sync_manager_telegram_ids(self, apply):
        """Sync telegram_user_id from CustomUser to ManagerProfile."""
        self.stdout.write(self.style.HTTP_INFO('=== Syncing Manager Telegram IDs ==='))

        # Find managers with telegram_user_id set on CustomUser but not on profile
        managers_to_sync = []

        for profile in ManagerProfile.objects.select_related('user').all():
            user = profile.user
            # User has telegram_id but profile doesn't
            if user.telegram_user_id and not profile.telegram_user_id:
                managers_to_sync.append((profile, user.telegram_user_id, user.telegram_username))

        self.stdout.write(f'Total ManagerProfiles: {ManagerProfile.objects.count()}')
        self.stdout.write(f'Profiles needing sync: {len(managers_to_sync)}')

        if not managers_to_sync:
            self.stdout.write(self.style.SUCCESS('All manager profiles are in sync!'))
            return

        updated = 0
        for profile, telegram_id, telegram_username in managers_to_sync:
            if apply:
                with transaction.atomic():
                    profile.telegram_user_id = telegram_id
                    if telegram_username and not profile.telegram_username:
                        profile.telegram_username = telegram_username
                    profile.save(update_fields=['telegram_user_id', 'telegram_username'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  UPDATED: {profile.user.first_name} - telegram_id={telegram_id}'
                    )
                )
            else:
                self.stdout.write(
                    f'  WOULD UPDATE: {profile.user.first_name} - telegram_id={telegram_id}'
                )
            updated += 1

        self.stdout.write(f'\nManager profiles updated: {updated}')

    def sync_customer_telegram_ids(self, apply):
        """Sync telegram_user_id from CustomUser to CustomerProfile."""
        self.stdout.write(self.style.HTTP_INFO('=== Syncing Customer Telegram IDs ==='))

        # Find customers with telegram_user_id set on CustomUser but not on profile
        customers_to_sync = []

        for profile in CustomerProfile.objects.select_related('user').all():
            user = profile.user
            # User has telegram_id but profile doesn't
            if user.telegram_user_id and not profile.telegram_user_id:
                customers_to_sync.append((profile, user.telegram_user_id, user.telegram_username))

        self.stdout.write(f'Total CustomerProfiles: {CustomerProfile.objects.count()}')
        self.stdout.write(f'Profiles needing sync: {len(customers_to_sync)}')

        if not customers_to_sync:
            self.stdout.write(self.style.SUCCESS('All customer profiles are in sync!'))
            return

        updated = 0
        for profile, telegram_id, telegram_username in customers_to_sync:
            if apply:
                with transaction.atomic():
                    profile.telegram_user_id = telegram_id
                    if telegram_username and not profile.telegram_username:
                        profile.telegram_username = telegram_username
                    profile.save(update_fields=['telegram_user_id', 'telegram_username'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  UPDATED: {profile.user.first_name} - telegram_id={telegram_id}'
                    )
                )
            else:
                self.stdout.write(
                    f'  WOULD UPDATE: {profile.user.first_name} - telegram_id={telegram_id}'
                )
            updated += 1

        self.stdout.write(f'\nCustomer profiles updated: {updated}')
