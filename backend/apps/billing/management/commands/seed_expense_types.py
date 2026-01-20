"""
Management command to seed predefined expense types.

Usage:
    python manage.py seed_expense_types
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.billing.models import ExpenseType


class Command(BaseCommand):
    help = "Seed predefined expense types for additional charges"

    # Common expense types for container terminal operations
    EXPENSE_TYPES = [
        {
            "name": "Кран",
            "default_rate_usd": Decimal("25.00"),
            "default_rate_uzs": Decimal("320000"),
        },
        {
            "name": "Досмотр",
            "default_rate_usd": Decimal("15.00"),
            "default_rate_uzs": Decimal("190000"),
        },
        {
            "name": "Перестановка",
            "default_rate_usd": Decimal("20.00"),
            "default_rate_uzs": Decimal("255000"),
        },
        {
            "name": "Погрузка",
            "default_rate_usd": Decimal("30.00"),
            "default_rate_uzs": Decimal("385000"),
        },
        {
            "name": "Разгрузка",
            "default_rate_usd": Decimal("30.00"),
            "default_rate_uzs": Decimal("385000"),
        },
        {
            "name": "Взвешивание",
            "default_rate_usd": Decimal("10.00"),
            "default_rate_uzs": Decimal("128000"),
        },
        {
            "name": "Пломбирование",
            "default_rate_usd": Decimal("5.00"),
            "default_rate_uzs": Decimal("64000"),
        },
        {
            "name": "Хранение сверхнормативное",
            "default_rate_usd": Decimal("50.00"),
            "default_rate_uzs": Decimal("640000"),
        },
    ]

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for expense_data in self.EXPENSE_TYPES:
            expense_type, created = ExpenseType.objects.update_or_create(
                name=expense_data["name"],
                defaults={
                    "default_rate_usd": expense_data["default_rate_usd"],
                    "default_rate_uzs": expense_data["default_rate_uzs"],
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created: {expense_type.name}")
                )
            else:
                updated_count += 1
                self.stdout.write(f"  Updated: {expense_type.name}")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created_count}, Updated: {updated_count}"
            )
        )
