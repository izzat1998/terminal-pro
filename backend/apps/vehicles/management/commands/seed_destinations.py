"""
Django management command to seed terminal destinations with zones
Usage: python manage.py seed_destinations [--clear]
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.vehicles.models import Destination


class Command(BaseCommand):
    help = "Seed terminal destinations with their zones"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing destinations before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        clear = options.get("clear", False)

        # Terminal destinations with zones (code is based on zone for uniqueness)
        destinations_data = [
            {"name": "KALMAR", "zone": "K1", "code": "kalmar-k1"},
            {"name": "Кран 45т", "zone": "K2", "code": "kran45t-k2"},
            {"name": "Брусчатка", "zone": "K3", "code": "bruschatka-k3"},
            {"name": "Ремонт", "zone": "K4", "code": "remont-k4"},
            {"name": "Гараж", "zone": "K5", "code": "garazh-k5"},
            {"name": "Холодильник", "zone": "X1", "code": "kholodilnik-x1"},
            {"name": "Подвал", "zone": "P1", "code": "podval-p1"},
            {"name": "Склад-1", "zone": "U1", "code": "sklad1-u1"},
            {"name": "Навес-2", "zone": "H2", "code": "naves2-h2"},
            {"name": "Навес-1", "zone": "H1", "code": "naves1-h1"},
            {"name": "Меб.Склад", "zone": "M1", "code": "mebsklad-m1"},
            {"name": "Метал", "zone": "M2", "code": "metal-m2"},
            {"name": "Офис", "zone": "O1", "code": "ofis-o1"},
        ]

        # Clear existing destinations if requested
        if clear:
            deleted_count = Destination.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted_count} existing destinations")
            )

        # Create destinations
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for data in destinations_data:
            name = data["name"]
            zone = data["zone"]
            code = data["code"]

            # Check if destination already exists
            destination, created = Destination.objects.get_or_create(
                name=name, defaults={"zone": zone, "code": code}
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✓ Created: {name} ({zone})"))
            else:
                # Update zone if different
                if destination.zone != zone:
                    destination.zone = zone
                    destination.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"↻ Updated zone: {name} → {zone}")
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.NOTICE(f"− Skipped (exists): {name} ({zone})")
                    )

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Created:  {created_count} destinations")
        self.stdout.write(f"Updated:  {updated_count} destinations")
        self.stdout.write(f"Skipped:  {skipped_count} destinations")
        self.stdout.write(
            f"Total:    {Destination.objects.count()} destinations in database"
        )
        self.stdout.write(self.style.SUCCESS("=" * 60))
