"""
Seed TelegramActivityLog entries for existing data.

Creates realistic activity logs as if actions were performed via Telegram bot.
Links to existing ContainerEntry, CraneOperation, and PreOrder records.
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import ManagerProfile, CustomerProfile
from apps.core.models import TelegramActivityLog
from apps.terminal_operations.models import ContainerEntry, CraneOperation, PreOrder


User = get_user_model()


class Command(BaseCommand):
    help = "Seed TelegramActivityLog entries for existing containers and operations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing activity logs before seeding",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of entries to process (default: all)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing telegram activity logs...")
            count = TelegramActivityLog.objects.count()
            TelegramActivityLog.objects.all().delete()
            self.stdout.write(f"  Deleted {count} activity logs")

        self.stdout.write(self.style.NOTICE("Starting telegram activity seeding..."))

        # Get managers with bot access for assigning as action performers
        managers = self._get_or_create_bot_managers()
        if not managers:
            self.stdout.write(
                self.style.ERROR("No managers available. Create managers first.")
            )
            return

        # Get customers for pre-order activities
        customers = self._get_or_create_bot_customers()

        limit = options.get("limit")

        # 1. Create activity logs for container entries
        entry_logs = self._seed_entry_activities(managers, limit)
        self.stdout.write(f"  Created {entry_logs} container entry activity logs")

        # 2. Create activity logs for container exits
        exit_logs = self._seed_exit_activities(managers, limit)
        self.stdout.write(f"  Created {exit_logs} container exit activity logs")

        # 3. Create activity logs for crane operations
        crane_logs = self._seed_crane_activities(managers, limit)
        self.stdout.write(f"  Created {crane_logs} crane operation activity logs")

        # 4. Create activity logs for pre-orders
        if customers:
            preorder_logs = self._seed_preorder_activities(customers, limit)
            self.stdout.write(f"  Created {preorder_logs} pre-order activity logs")
        else:
            self.stdout.write("  No customers available, skipping pre-order logs")

        total = entry_logs + exit_logs + crane_logs
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {total} telegram activity logs!")
        )

    def _get_or_create_bot_managers(self):
        """Get managers with telegram access, or assign fake telegram IDs."""
        # First try to get managers with telegram_user_id via profile
        managers_with_telegram = []

        profiles = ManagerProfile.objects.select_related("user").filter(
            user__is_active=True,
            telegram_user_id__isnull=False,
        )

        for profile in profiles:
            managers_with_telegram.append(
                {
                    "user": profile.user,
                    "telegram_user_id": profile.telegram_user_id,
                }
            )

        # If no managers have telegram IDs, assign fake ones
        if not managers_with_telegram:
            self.stdout.write("  No managers with Telegram IDs, assigning fake IDs...")
            profiles = ManagerProfile.objects.select_related("user").filter(
                user__is_active=True
            )[:5]

            for i, profile in enumerate(profiles):
                fake_telegram_id = 100000000 + i
                profile.telegram_user_id = fake_telegram_id
                profile.bot_access = True
                profile.save()
                managers_with_telegram.append(
                    {
                        "user": profile.user,
                        "telegram_user_id": fake_telegram_id,
                    }
                )

        # Fallback: check legacy fields on User model
        if not managers_with_telegram:
            users = User.objects.filter(
                user_type="manager",
                is_active=True,
            )[:5]

            for i, user in enumerate(users):
                fake_telegram_id = 100000000 + i
                user.telegram_user_id = fake_telegram_id
                user.bot_access = True
                user.save()
                managers_with_telegram.append(
                    {
                        "user": user,
                        "telegram_user_id": fake_telegram_id,
                    }
                )

        return managers_with_telegram

    def _get_or_create_bot_customers(self):
        """Get customers with telegram access, or assign fake telegram IDs."""
        customers_with_telegram = []

        profiles = CustomerProfile.objects.select_related("user").filter(
            user__is_active=True,
            telegram_user_id__isnull=False,
        )

        for profile in profiles:
            customers_with_telegram.append(
                {
                    "user": profile.user,
                    "telegram_user_id": profile.telegram_user_id,
                }
            )

        # If no customers have telegram IDs, assign fake ones
        if not customers_with_telegram:
            self.stdout.write("  No customers with Telegram IDs, assigning fake IDs...")
            profiles = CustomerProfile.objects.select_related("user").filter(
                user__is_active=True
            )[:3]

            for i, profile in enumerate(profiles):
                fake_telegram_id = 200000000 + i
                profile.telegram_user_id = fake_telegram_id
                profile.bot_access = True
                profile.save()
                customers_with_telegram.append(
                    {
                        "user": profile.user,
                        "telegram_user_id": fake_telegram_id,
                    }
                )

        return customers_with_telegram

    def _seed_entry_activities(self, managers, limit=None):
        """Create activity logs for container entries."""
        # Get entries that don't have activity logs yet
        existing_entry_ids = TelegramActivityLog.objects.filter(
            action="container_entry_created",
            content_type=ContentType.objects.get_for_model(ContainerEntry),
        ).values_list("object_id", flat=True)

        entries = ContainerEntry.objects.exclude(id__in=existing_entry_ids).select_related(
            "container"
        )

        if limit:
            entries = entries[:limit]

        content_type = ContentType.objects.get_for_model(ContainerEntry)
        logs_created = 0

        for entry in entries:
            manager = random.choice(managers)

            # Create activity log with timestamp slightly after entry_time
            log_time = entry.entry_time + timedelta(seconds=random.randint(30, 300))

            TelegramActivityLog.objects.create(
                user=manager["user"],
                user_type="manager",
                telegram_user_id=manager["telegram_user_id"],
                action="container_entry_created",
                content_type=content_type,
                object_id=entry.id,
                details={
                    "container_number": entry.container.container_number,
                    "status": entry.status,
                    "transport_type": entry.transport_type,
                    "transport_number": entry.transport_number or "",
                },
                success=True,
                created_at=log_time,
            )
            logs_created += 1

        return logs_created

    def _seed_exit_activities(self, managers, limit=None):
        """Create activity logs for container exits."""
        # Get entries with exit_date that don't have exit activity logs
        existing_exit_ids = TelegramActivityLog.objects.filter(
            action="container_exit_recorded",
            content_type=ContentType.objects.get_for_model(ContainerEntry),
        ).values_list("object_id", flat=True)

        entries = ContainerEntry.objects.filter(
            exit_date__isnull=False
        ).exclude(
            id__in=existing_exit_ids
        ).select_related("container")

        if limit:
            entries = entries[:limit]

        content_type = ContentType.objects.get_for_model(ContainerEntry)
        logs_created = 0

        for entry in entries:
            manager = random.choice(managers)

            # Create activity log with timestamp slightly after exit_date
            if entry.exit_date:
                # exit_date is a DateField, convert to datetime
                exit_datetime = timezone.make_aware(
                    timezone.datetime.combine(entry.exit_date, timezone.datetime.min.time())
                )
                log_time = exit_datetime + timedelta(
                    hours=random.randint(8, 18),
                    minutes=random.randint(0, 59),
                )
            else:
                log_time = timezone.now()

            TelegramActivityLog.objects.create(
                user=manager["user"],
                user_type="manager",
                telegram_user_id=manager["telegram_user_id"],
                action="container_exit_recorded",
                content_type=content_type,
                object_id=entry.id,
                details={
                    "container_number": entry.container.container_number,
                    "exit_date": str(entry.exit_date) if entry.exit_date else "",
                    "exit_transport_type": entry.exit_transport_type or "",
                    "exit_transport_number": entry.exit_transport_number or "",
                },
                success=True,
                created_at=log_time,
            )
            logs_created += 1

        return logs_created

    def _seed_crane_activities(self, managers, limit=None):
        """Create activity logs for crane operations."""
        # Get crane operations that don't have activity logs
        existing_crane_ids = TelegramActivityLog.objects.filter(
            action="crane_operation_added",
            content_type=ContentType.objects.get_for_model(CraneOperation),
        ).values_list("object_id", flat=True)

        operations = CraneOperation.objects.exclude(
            id__in=existing_crane_ids
        ).select_related("container_entry__container")

        if limit:
            operations = operations[:limit]

        content_type = ContentType.objects.get_for_model(CraneOperation)
        logs_created = 0

        for operation in operations:
            manager = random.choice(managers)

            # Create activity log with timestamp slightly after operation_date
            log_time = operation.operation_date + timedelta(
                seconds=random.randint(30, 300)
            )

            TelegramActivityLog.objects.create(
                user=manager["user"],
                user_type="manager",
                telegram_user_id=manager["telegram_user_id"],
                action="crane_operation_added",
                content_type=content_type,
                object_id=operation.id,
                details={
                    "container_number": operation.container_entry.container.container_number,
                    "operation_date": str(operation.operation_date),
                },
                success=True,
                created_at=log_time,
            )
            logs_created += 1

        return logs_created

    def _seed_preorder_activities(self, customers, limit=None):
        """Create activity logs for pre-orders."""
        # Get pre-orders that don't have activity logs
        existing_preorder_ids = TelegramActivityLog.objects.filter(
            action__in=["preorder_created", "preorder_cancelled"],
            content_type=ContentType.objects.get_for_model(PreOrder),
        ).values_list("object_id", flat=True)

        preorders = PreOrder.objects.exclude(id__in=existing_preorder_ids)

        if limit:
            preorders = preorders[:limit]

        content_type = ContentType.objects.get_for_model(PreOrder)
        logs_created = 0

        for preorder in preorders:
            # Try to use the actual customer, fallback to random
            customer_user = preorder.customer
            customer_data = None

            # Find matching customer in our list
            for c in customers:
                if c["user"].id == customer_user.id:
                    customer_data = c
                    break

            # If customer not in list, use random one
            if not customer_data:
                customer_data = random.choice(customers)

            # Create "preorder_created" log
            log_time = preorder.created_at + timedelta(seconds=random.randint(1, 60))

            TelegramActivityLog.objects.create(
                user=customer_data["user"],
                user_type="customer",
                telegram_user_id=customer_data["telegram_user_id"],
                action="preorder_created",
                content_type=content_type,
                object_id=preorder.id,
                details={
                    "plate_number": preorder.plate_number,
                    "operation_type": preorder.operation_type,
                    "status": "PENDING",
                    "batch_id": preorder.batch_id or "",
                },
                success=True,
                created_at=log_time,
            )
            logs_created += 1

            # If cancelled, also create cancelled log
            if preorder.status == "CANCELLED" and preorder.cancelled_at:
                cancel_time = preorder.cancelled_at + timedelta(
                    seconds=random.randint(1, 60)
                )
                TelegramActivityLog.objects.create(
                    user=customer_data["user"],
                    user_type="customer",
                    telegram_user_id=customer_data["telegram_user_id"],
                    action="preorder_cancelled",
                    content_type=content_type,
                    object_id=preorder.id,
                    details={
                        "plate_number": preorder.plate_number,
                        "operation_type": preorder.operation_type,
                        "status": "CANCELLED",
                        "batch_id": preorder.batch_id or "",
                    },
                    success=True,
                    created_at=cancel_time,
                )
                logs_created += 1

        return logs_created
