"""
Management command to populate container positions for 3D visualization testing.

Enforces ISO stacking rules:
1. Support rule: Containers above tier 1 need support below
2. Size rule: 40ft cannot be placed on 20ft (corner posts don't align)
3. Weight rule: Laden containers cannot be placed on empty containers
"""

import random

from django.core.management.base import BaseCommand

from apps.terminal_operations.models import ContainerEntry, ContainerPosition


def get_container_size(iso_type: str) -> str:
    """Get container size from ISO type code."""
    if not iso_type:
        return "20ft"
    first_char = iso_type[0]
    if first_char == "2":
        return "20ft"
    elif first_char == "4":
        return "40ft"
    elif first_char in ("L", "9"):
        return "45ft"
    return "20ft"


class Command(BaseCommand):
    help = "Populate container positions with valid ISO stacking rules"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing positions before populating",
        )
        parser.add_argument(
            "--max-containers",
            type=int,
            default=50,
            help="Maximum containers to position (default: 50)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted = ContainerPosition.objects.all().delete()
            self.stdout.write(f"Cleared {deleted[0]} existing positions")

        # Get containers on terminal (no exit_date), not yet positioned
        containers = list(
            ContainerEntry.objects.filter(exit_date__isnull=True)
            .exclude(position__isnull=False)
            .select_related("container")[: options["max_containers"]]
        )

        if not containers:
            self.stdout.write(self.style.WARNING("No containers to position"))
            return

        self.stdout.write(f"Found {len(containers)} containers to position")

        # Sort containers for proper stacking:
        # 1. Laden containers first (they go at bottom)
        # 2. Then 40ft before 20ft (40ft needs clear slots)
        containers.sort(
            key=lambda c: (
                0 if c.status == "LADEN" else 1,  # Laden first
                0
                if get_container_size(c.container.iso_type) in ("40ft", "45ft")
                else 1,
            )
        )

        # Currently only Zone A for testing
        zone = "A"
        max_rows = 10
        max_bays = 10
        max_tiers = 4

        # Track positions: (row, bay, tier) -> ContainerEntry
        positions = {}

        # Load existing positions
        for pos in ContainerPosition.objects.filter(zone=zone):
            positions[(pos.row, pos.bay, pos.tier)] = pos.container_entry

        assigned = 0
        skipped = 0

        for container in containers:
            container_size = get_container_size(container.container.iso_type)
            is_laden = container.status == "LADEN"

            # Find valid position
            position = self._find_valid_position(
                container_size=container_size,
                is_laden=is_laden,
                positions=positions,
                max_rows=max_rows,
                max_bays=max_bays,
                max_tiers=max_tiers,
            )

            if position is None:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ✗ {container.container.container_number} - no valid position"
                    )
                )
                continue

            row, bay, tier = position

            # Create position record
            ContainerPosition.objects.create(
                container_entry=container,
                zone=zone,
                row=row,
                bay=bay,
                tier=tier,
                auto_assigned=True,
            )
            positions[(row, bay, tier)] = container
            assigned += 1

            coord = f"{zone}-R{row:02d}-B{bay:02d}-T{tier}"
            size_label = container_size
            status_label = "LADEN" if is_laden else "EMPTY"
            self.stdout.write(
                f"  ✓ {container.container.container_number} ({size_label}, {status_label}) -> {coord}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Assigned {assigned} positions successfully!")
        )
        if skipped:
            self.stdout.write(
                self.style.WARNING(f"Skipped {skipped} containers (no valid positions)")
            )

    def _find_valid_position(
        self,
        container_size: str,
        is_laden: bool,
        positions: dict,
        max_rows: int,
        max_bays: int,
        max_tiers: int,
    ) -> tuple | None:
        """
        Find a valid position for container following ISO stacking rules.

        Rules:
        1. Position must be empty
        2. Tier > 1 needs support below
        3. 40ft cannot stack on 20ft
        4. Laden cannot stack on empty
        """
        # Try random positions to spread containers naturally
        attempts = [
            (row, bay)
            for row in range(1, max_rows + 1)
            for bay in range(1, max_bays + 1)
        ]
        random.shuffle(attempts)

        for row, bay in attempts:
            for tier in range(1, max_tiers + 1):
                if (row, bay, tier) in positions:
                    continue  # Position occupied

                # Rule: Support needed for tier > 1
                if tier > 1 and (row, bay, tier - 1) not in positions:
                    continue

                # Rules for stacking on existing container
                if tier > 1:
                    below_container = positions[(row, bay, tier - 1)]
                    below_size = get_container_size(below_container.container.iso_type)
                    below_is_laden = below_container.status == "LADEN"

                    # Rule: 40ft/45ft cannot be placed on 20ft
                    if container_size in ("40ft", "45ft") and below_size == "20ft":
                        continue

                    # Rule: Laden cannot be placed on empty
                    if is_laden and not below_is_laden:
                        continue

                # Valid position found
                return (row, bay, tier)

        return None
