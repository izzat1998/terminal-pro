"""
Seed tariff data for testing and demo purposes.

Creates:
- 1 general tariff (applies to all companies without special tariffs)
- Special tariffs for ~50% of companies with varied pricing

Usage:
    python manage.py seed_tariffs
    python manage.py seed_tariffs --clear  # Clear existing tariffs first
"""

import random
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounts.models import Company, CustomUser
from apps.billing.models import (
    Tariff,
    TariffRate,
)


class Command(BaseCommand):
    help = "Seed tariff data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing tariffs before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing tariffs...")
            TariffRate.objects.all().delete()
            Tariff.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared all tariffs"))

        # Get admin user for created_by
        admin_user = CustomUser.objects.filter(
            user_type="admin", is_active=True
        ).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No active admin user found. Create one first.")
            )
            return

        effective_from = date(2026, 1, 1)

        # Base rates for general tariff
        base_rates = {
            ("20ft", "laden"): {
                "usd": Decimal("3.50"),
                "uzs": Decimal("42000"),
                "free_days": 5,
            },
            ("20ft", "empty"): {
                "usd": Decimal("2.50"),
                "uzs": Decimal("30000"),
                "free_days": 7,
            },
            ("40ft", "laden"): {
                "usd": Decimal("5.50"),
                "uzs": Decimal("66000"),
                "free_days": 5,
            },
            ("40ft", "empty"): {
                "usd": Decimal("4.00"),
                "uzs": Decimal("48000"),
                "free_days": 7,
            },
        }

        # Create general tariff
        self.stdout.write("\nCreating general tariff...")
        general_tariff, created = Tariff.objects.get_or_create(
            company=None,
            effective_from=effective_from,
            defaults={
                "effective_to": None,
                "created_by": admin_user,
                "notes": "Общий тариф на 2026 год",
            },
        )

        if created:
            for (size, status), rates in base_rates.items():
                TariffRate.objects.create(
                    tariff=general_tariff,
                    container_size=size,
                    container_status=status,
                    daily_rate_usd=rates["usd"],
                    daily_rate_uzs=rates["uzs"],
                    free_days=rates["free_days"],
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ General tariff created (ID: {general_tariff.id})"
                )
            )
        else:
            self.stdout.write(
                f"  - General tariff already exists (ID: {general_tariff.id})"
            )

        # Get all companies
        companies = list(Company.objects.filter(is_active=True))
        if not companies:
            self.stdout.write(
                self.style.WARNING(
                    "No active companies found. Skipping special tariffs."
                )
            )
            return

        # Select 50% of companies for special tariffs
        num_special = max(1, len(companies) // 2)
        selected_companies = random.sample(companies, num_special)

        self.stdout.write(
            f"\nCreating special tariffs for {num_special} of {len(companies)} companies..."
        )

        created_count = 0
        skipped_count = 0

        for company in selected_companies:
            # Check if tariff already exists
            existing = Tariff.objects.filter(
                company=company,
                effective_from=effective_from,
            ).exists()

            if existing:
                skipped_count += 1
                continue

            # Generate varied pricing (discount or premium)
            # Discount: 5-20% off base rates
            # Premium: 5-15% above base rates (for smaller clients)
            price_factor = random.choice(
                [
                    Decimal("0.80"),  # 20% discount
                    Decimal("0.85"),  # 15% discount
                    Decimal("0.90"),  # 10% discount
                    Decimal("0.95"),  # 5% discount
                    Decimal("1.00"),  # Same as general
                    Decimal("1.05"),  # 5% premium
                    Decimal("1.10"),  # 10% premium
                ]
            )

            # Vary free days too
            free_days_bonus = random.choice([0, 1, 2, 3, 5])

            # Create special tariff
            special_tariff = Tariff.objects.create(
                company=company,
                effective_from=effective_from,
                effective_to=None,
                created_by=admin_user,
                notes=f"Специальный тариф для {company.name}",
            )

            for (size, status), rates in base_rates.items():
                # Apply price factor and round
                usd_rate = (rates["usd"] * price_factor).quantize(Decimal("0.01"))
                uzs_rate = (rates["uzs"] * price_factor).quantize(Decimal("1"))
                free_days = rates["free_days"] + free_days_bonus

                TariffRate.objects.create(
                    tariff=special_tariff,
                    container_size=size,
                    container_status=status,
                    daily_rate_usd=usd_rate,
                    daily_rate_uzs=uzs_rate,
                    free_days=free_days,
                )

            created_count += 1
            discount_pct = int((1 - price_factor) * 100)
            if discount_pct > 0:
                price_label = f"{discount_pct}% скидка"
            elif discount_pct < 0:
                price_label = f"{-discount_pct}% надбавка"
            else:
                price_label = "базовая цена"

            self.stdout.write(
                f"  ✓ {company.name}: {price_label}, +{free_days_bonus} дней"
            )

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Tariff seeding complete!"))
        self.stdout.write("  General tariff: 1")
        self.stdout.write(f"  Special tariffs created: {created_count}")
        self.stdout.write(f"  Special tariffs skipped (already exist): {skipped_count}")
        self.stdout.write(self.style.SUCCESS("=" * 50))

        # Show sample rates
        self.stdout.write("\nGeneral tariff rates:")
        for rate in general_tariff.rates.all():
            self.stdout.write(
                f"  {rate.get_container_size_display()} {rate.get_container_status_display()}: "
                f"${rate.daily_rate_usd}/день, {rate.free_days} беспл. дней"
            )
