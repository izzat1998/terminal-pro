"""
Import yard slots from frontend containers.json into ContainerPosition model.

Reads DXF-extracted container positions and creates database records with both
logical (zone/row/bay/tier) and physical (dxf_x/dxf_y/rotation) coordinates.

Usage:
    python manage.py import_yard_slots
    python manage.py import_yard_slots --clear  # Delete existing slots first
"""

import json
import os

from django.core.management.base import BaseCommand

from apps.terminal_operations.models import ContainerPosition


class Command(BaseCommand):
    help = "Import yard slots from frontend containers.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing ContainerPosition records before importing",
        )
        parser.add_argument(
            "--json-path",
            type=str,
            default=None,
            help="Path to containers.json (default: auto-detect from project root)",
        )

    def handle(self, *args, **options):
        # Find containers.json
        json_path = options["json_path"]
        if not json_path:
            # Auto-detect from project structure
            base_dir = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        )
                    )
                )
            )
            json_path = os.path.join(base_dir, "frontend", "src", "data", "containers.json")

        if not os.path.exists(json_path):
            self.stderr.write(self.style.ERROR(f"File not found: {json_path}"))
            return

        with open(json_path) as f:
            containers = json.load(f)

        self.stdout.write(f"Loaded {len(containers)} container positions from JSON")

        if options["clear"]:
            deleted_count = ContainerPosition.objects.count()
            ContainerPosition.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} existing positions"))

        # Group containers by Y coordinate band to assign zones
        # Main cluster: Y ~73300-73500 → zones A/B/C
        # Outliers: Y ~500 → zone D
        zones = self._assign_zones(containers)

        created = 0
        skipped = 0

        for zone_name, zone_containers in sorted(zones.items()):
            # Sort by X (row) then Y (bay) within each zone
            zone_containers.sort(key=lambda c: (c["_original"]["x"], c["_original"]["y"]))

            # Assign row/bay by grid position
            # Group by X coordinate (with tolerance) → rows
            rows = self._group_by_coordinate(
                zone_containers, axis="x", tolerance=3.0
            )

            for row_idx, row_containers in enumerate(rows, start=1):
                # Sort by Y within each row → bays
                row_containers.sort(key=lambda c: c["_original"]["y"])

                for bay_idx, container in enumerate(row_containers, start=1):
                    # Determine container size from blockName
                    block = container.get("blockName", "40ft")
                    size = "20ft" if "20" in block else "40ft"

                    # Check if slot already exists at these coordinates
                    existing = ContainerPosition.objects.filter(
                        zone=zone_name,
                        row=row_idx,
                        bay=bay_idx,
                        tier=1,
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                    ContainerPosition.objects.create(
                        zone=zone_name,
                        row=row_idx,
                        bay=bay_idx,
                        tier=1,
                        sub_slot="A",
                        dxf_x=container["_original"]["x"],
                        dxf_y=container["_original"]["y"],
                        rotation=container["rotation"],
                        container_size=size,
                        container_entry=None,  # Empty slot
                    )
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} yard slots, skipped {skipped} (already exist)"
            )
        )

        # Print summary
        for zone_name in sorted(zones.keys()):
            count = ContainerPosition.objects.filter(zone=zone_name).count()
            self.stdout.write(f"  Zone {zone_name}: {count} slots")

    def _assign_zones(self, containers):
        """Group containers into zones based on Y coordinate."""
        zones = {}
        zone_labels = ["A", "B", "C", "D", "E"]
        zone_idx = 0

        # Sort by Y to find natural breaks
        sorted_containers = sorted(containers, key=lambda c: c["_original"]["y"])

        # Find Y-coordinate clusters (gap > 100m = new zone)
        current_zone = []
        prev_y = None

        for c in sorted_containers:
            y = c["_original"]["y"]
            if prev_y is not None and abs(y - prev_y) > 100:
                # Large gap — start new zone
                if current_zone:
                    label = zone_labels[zone_idx] if zone_idx < len(zone_labels) else f"Z{zone_idx}"
                    zones[label] = current_zone
                    zone_idx += 1
                current_zone = []
            current_zone.append(c)
            prev_y = y

        # Last zone
        if current_zone:
            label = zone_labels[zone_idx] if zone_idx < len(zone_labels) else f"Z{zone_idx}"
            zones[label] = current_zone

        return zones

    def _group_by_coordinate(self, containers, axis, tolerance):
        """Group containers by X or Y coordinate with tolerance."""
        if not containers:
            return []

        key = lambda c: c["_original"]["x"] if axis == "x" else c["_original"]["y"]
        sorted_c = sorted(containers, key=key)

        groups = [[sorted_c[0]]]
        for c in sorted_c[1:]:
            if abs(key(c) - key(groups[-1][-1])) <= tolerance:
                groups[-1].append(c)
            else:
                groups.append([c])

        return groups
