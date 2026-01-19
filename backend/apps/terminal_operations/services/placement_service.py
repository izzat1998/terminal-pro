"""
Placement Service - Business logic for 3D terminal container placement.

Handles auto-suggest algorithm, position validation, and stacking rules.
"""

from typing import Optional

from django.db import IntegrityError, transaction
from django.db.models import Count

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService
from apps.terminal_operations.models import ContainerEntry, ContainerPosition, WorkOrder


class PositionOccupiedError(BusinessLogicError):
    """Raised when trying to assign an already occupied position."""

    def __init__(self, coordinate: str):
        super().__init__(
            message=f"Позиция {coordinate} уже занята",
            error_code="POSITION_OCCUPIED",
            details={"coordinate": coordinate},
        )


class NoSupportError(BusinessLogicError):
    """Raised when placing container above tier 1 without support below."""

    def __init__(self, coordinate: str):
        super().__init__(
            message=f"Нет контейнера ниже для поддержки в позиции {coordinate}",
            error_code="NO_SUPPORT",
            details={"coordinate": coordinate},
        )


class NoAvailablePositionsError(BusinessLogicError):
    """Raised when no positions are available for placement."""

    def __init__(self, zone: Optional[str] = None):
        if zone:
            message = f"Нет свободных позиций в зоне {zone}"
            details = {"zone": zone}
        else:
            message = "Нет свободных позиций на терминале"
            details = None
        super().__init__(
            message=message,
            error_code="NO_AVAILABLE_POSITIONS",
            details=details,
        )


class ContainerAlreadyPlacedError(BusinessLogicError):
    """Raised when container already has a position assigned."""

    def __init__(self, container_number: str, coordinate: str):
        super().__init__(
            message=f"Контейнер {container_number} уже размещён в позиции {coordinate}",
            error_code="ALREADY_PLACED",
            details={
                "container_number": container_number,
                "current_coordinate": coordinate,
            },
        )


class SizeCompatibilityError(BusinessLogicError):
    """Raised when container size is incompatible with container below."""

    def __init__(self, coordinate: str, top_size: str, bottom_size: str):
        super().__init__(
            message=f"Контейнер {top_size} не может быть размещён над контейнером {bottom_size}. "
            f"ISO стандарт: 40ft контейнер должен располагаться над двумя 20ft контейнерами.",
            error_code="SIZE_INCOMPATIBLE",
            details={
                "coordinate": coordinate,
                "top_container_size": top_size,
                "bottom_container_size": bottom_size,
                "rule": "40ft containers must be placed on 40ft containers or two 20ft containers (corner alignment)",
            },
        )


class WeightDistributionError(BusinessLogicError):
    """Raised when laden container is placed above empty container."""

    def __init__(self, coordinate: str):
        super().__init__(
            message="Гружёный контейнер не может быть размещён над порожним. "
            "ISO стандарт: тяжёлые контейнеры снизу, лёгкие сверху.",
            error_code="WEIGHT_DISTRIBUTION_VIOLATION",
            details={
                "coordinate": coordinate,
                "rule": "Heavy (laden) containers must be at bottom, light (empty) at top",
            },
        )


class RowSegregationError(BusinessLogicError):
    """Raised when container is placed in wrong row for its size."""

    def __init__(self, coordinate: str, container_size: str, allowed_rows: list):
        super().__init__(
            message=f"Контейнер {container_size} должен быть размещён в рядах {allowed_rows[0]}-{allowed_rows[-1]}. "
            f"Правило TOS: разные размеры контейнеров в разных рядах.",
            error_code="ROW_SEGREGATION_VIOLATION",
            details={
                "coordinate": coordinate,
                "container_size": container_size,
                "allowed_rows": allowed_rows,
                "rule": "40ft containers in rows 1-5, 20ft containers in rows 6-10",
            },
        )


# Terminal configuration constants
# Currently only Zone A for testing
ZONES = ["A"]
ALL_ZONES = ["A", "B", "C", "D", "E"]  # For future expansion
MAX_ROWS = 10
MAX_BAYS = 10
MAX_TIERS = 4

# Row segregation by container size (TOS best practice)
# Separating sizes prevents corner post misalignment issues
ROWS_40FT = [1, 2, 3, 4, 5]  # Rows 1-5 for 40ft containers
ROWS_20FT = [6, 7, 8, 9, 10]  # Rows 6-10 for 20ft containers

# Optimal stack height before spreading to next bay
# Industry standard: stack to 3 tiers for stability, then spread
PREFERRED_STACK_HEIGHT = 3


def format_coordinate(
    zone: str, row: int, bay: int, tier: int, sub_slot: str = "A"
) -> str:
    """Format position as coordinate string."""
    return f"{zone}-R{row:02d}-B{bay:02d}-T{tier}-{sub_slot}"


class PlacementService(BaseService):
    """
    Service for managing container placement in the 3D terminal yard.

    Provides:
    - Auto-suggest position algorithm
    - Position assignment with validation
    - Stacking rules enforcement
    - Layout data for visualization
    """

    def get_layout(self) -> dict:
        """
        Get complete terminal layout data for 3D visualization.

        Returns:
            dict with zones, dimensions, containers (placed + pending), and statistics
        """
        # Get all containers currently on terminal with positions
        entries_with_positions = (
            ContainerEntry.objects.filter(exit_date__isnull=True)
            .select_related("container", "position", "company")
            .prefetch_related("position")
        )

        containers = []
        for entry in entries_with_positions:
            if hasattr(entry, "position") and entry.position:
                containers.append(
                    {
                        "id": entry.id,
                        "container_number": entry.container.container_number,
                        "iso_type": entry.container.iso_type,
                        "status": entry.status,
                        "placement_status": "placed",  # Physically placed
                        "position": {
                            "zone": entry.position.zone,
                            "row": entry.position.row,
                            "bay": entry.position.bay,
                            "tier": entry.position.tier,
                            "sub_slot": entry.position.sub_slot,
                            "coordinate": entry.position.coordinate_string,
                        },
                        "entry_time": entry.entry_time.isoformat(),
                        "dwell_time_days": entry.dwell_time_days,
                        "company_name": (
                            entry.company.name if entry.company else entry.client_name
                        ),
                    }
                )

        # Get containers with active work orders (pending placement)
        # These show at their TARGET position with yellow pulsing effect
        active_work_order_statuses = ["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"]
        pending_work_orders = WorkOrder.objects.filter(
            status__in=active_work_order_statuses
        ).select_related(
            "container_entry__container",
            "container_entry__company",
            "assigned_to_vehicle",
        )

        for wo in pending_work_orders:
            entry = wo.container_entry
            containers.append(
                {
                    "id": entry.id,
                    "container_number": entry.container.container_number,
                    "iso_type": entry.container.iso_type,
                    "status": entry.status,
                    "placement_status": "pending",  # Work order created, awaiting physical placement
                    "work_order": {
                        "id": wo.id,
                        "order_number": wo.order_number,
                        "status": wo.status,
                        "priority": wo.priority,
                        "assigned_to": wo.assigned_to_vehicle.name if wo.assigned_to_vehicle else None,
                    },
                    "position": {
                        "zone": wo.target_zone,
                        "row": wo.target_row,
                        "bay": wo.target_bay,
                        "tier": wo.target_tier,
                        "sub_slot": wo.target_sub_slot,
                        "coordinate": format_coordinate(
                            wo.target_zone, wo.target_row, wo.target_bay, wo.target_tier, wo.target_sub_slot
                        ),
                    },
                    "entry_time": entry.entry_time.isoformat(),
                    "dwell_time_days": entry.dwell_time_days,
                    "company_name": (
                        entry.company.name if entry.company else entry.client_name
                    ),
                }
            )

        # Calculate statistics
        stats = self._calculate_stats()

        return {
            "zones": ZONES,
            "dimensions": {
                "max_rows": MAX_ROWS,
                "max_bays": MAX_BAYS,
                "max_tiers": MAX_TIERS,
            },
            "containers": containers,
            "stats": stats,
        }

    def _calculate_stats(self) -> dict:
        """Calculate terminal occupancy statistics."""
        total_capacity = len(ZONES) * MAX_ROWS * MAX_BAYS * MAX_TIERS

        # Count positions by zone
        zone_counts = (
            ContainerPosition.objects.values("zone")
            .annotate(count=Count("id"))
            .order_by("zone")
        )
        zone_occupied = {item["zone"]: item["count"] for item in zone_counts}

        total_occupied = ContainerPosition.objects.count()
        zone_capacity = MAX_ROWS * MAX_BAYS * MAX_TIERS

        by_zone = {}
        for zone in ZONES:
            occupied = zone_occupied.get(zone, 0)
            by_zone[zone] = {
                "occupied": occupied,
                "available": zone_capacity - occupied,
            }

        return {
            "total_capacity": total_capacity,
            "occupied": total_occupied,
            "available": total_capacity - total_occupied,
            "by_zone": by_zone,
        }

    def suggest_position(
        self,
        container_entry_id: int,
        zone_preference: Optional[str] = None,
    ) -> dict:
        """
        Auto-suggest optimal position for a container.

        Algorithm (simple greedy):
        1. If zone preference given, prioritize that zone
        2. Otherwise, find zone with most available ground-level slots
        3. Prefer tier 1 (ground level) for stability
        4. Fill sequentially (row by row, bay by bay)

        Args:
            container_entry_id: ContainerEntry to place
            zone_preference: Optional preferred zone (A-E)

        Returns:
            dict with suggested_position, reason, and alternatives

        Raises:
            ContainerAlreadyPlacedError: If container already has position
            NoAvailablePositionsError: If no positions available
        """
        # Get container entry
        try:
            entry = ContainerEntry.objects.select_related("container", "position").get(
                id=container_entry_id
            )
        except ContainerEntry.DoesNotExist:
            raise BusinessLogicError(
                message=f"Запись контейнера с ID {container_entry_id} не найдена",
                error_code="CONTAINER_ENTRY_NOT_FOUND",
            )

        # Check if already placed
        if hasattr(entry, "position") and entry.position:
            raise ContainerAlreadyPlacedError(
                entry.container.container_number,
                entry.position.coordinate_string,
            )

        # Get container size for size-aware placement
        container_size = self._get_container_size(entry.container.iso_type)

        # Find optimal position (size-aware with row segregation and sub-slots)
        suggested = self._find_optimal_position(zone_preference, container_size)
        if not suggested:
            raise NoAvailablePositionsError(zone_preference)

        # Find alternative positions (also size-aware)
        alternatives = self._find_alternatives(suggested, container_size, limit=3)

        zone, row, bay, tier, sub_slot = suggested
        reason = self._build_suggestion_reason(
            zone, row, tier, container_size, zone_preference
        )

        return {
            "suggested_position": {
                "zone": zone,
                "row": row,
                "bay": bay,
                "tier": tier,
                "sub_slot": sub_slot,
                "coordinate": format_coordinate(zone, row, bay, tier, sub_slot),
            },
            "reason": reason,
            "alternatives": [
                {
                    "zone": z,
                    "row": r,
                    "bay": b,
                    "tier": t,
                    "sub_slot": s,
                    "coordinate": format_coordinate(z, r, b, t, s),
                }
                for z, r, b, t, s in alternatives
            ],
        }

    def _get_rows_for_size(self, container_size: str) -> list:
        """Get allowed rows for a container size based on row segregation rules."""
        if container_size in ("40ft", "45ft"):
            return ROWS_40FT
        return ROWS_20FT

    def _get_sub_slots_for_size(self, container_size: str) -> list:
        """Get allowed sub-slots for a container size.

        - 40ft/45ft containers: Only slot A (they span the full bay)
        - 20ft containers: Both slots A and B (two can share a bay)
        """
        if container_size in ("40ft", "45ft"):
            return ["A"]
        return ["A", "B"]

    def _find_optimal_position(
        self,
        zone_preference: Optional[str] = None,
        container_size: str = "20ft",
    ) -> Optional[tuple]:
        """
        Find the best available position using TOS-compliant algorithm.

        Algorithm (consolidation-first):
        1. Get allowed rows for container size (row segregation)
        2. Get allowed sub-slots for container size (A for 40ft, A/B for 20ft)
        3. Prioritize consolidation: stack existing bays to PREFERRED_STACK_HEIGHT
        4. Fill row by row (complete one row before moving to next)
        5. Within a row, fill bay by bay with stacking

        This prevents random spreading and ensures efficient space usage.

        Args:
            zone_preference: Optional preferred zone (A-E)
            container_size: Container size ("20ft", "40ft", "45ft")

        Returns:
            Tuple of (zone, row, bay, tier, sub_slot) or None if no position available
        """
        zones = (
            [zone_preference] if zone_preference else self._get_zones_by_availability()
        )
        allowed_rows = self._get_rows_for_size(container_size)
        allowed_slots = self._get_sub_slots_for_size(container_size)

        for zone in zones:
            # Strategy: Fill bay-by-bay, row-by-row with stacking
            # This consolidates containers instead of spreading them

            for row in allowed_rows:
                for bay in range(1, MAX_BAYS + 1):
                    for sub_slot in allowed_slots:
                        # Try to stack on existing containers first (up to PREFERRED_STACK_HEIGHT)
                        for tier in range(1, PREFERRED_STACK_HEIGHT + 1):
                            if self._is_position_available(
                                zone, row, bay, tier, sub_slot
                            ):
                                if tier == 1 or self._has_support_below(
                                    zone, row, bay, tier, sub_slot
                                ):
                                    return (zone, row, bay, tier, sub_slot)
                                # If tier > 1 and no support, break to next bay/slot
                                break

            # Second pass: fill remaining tiers (above PREFERRED_STACK_HEIGHT) if needed
            for row in allowed_rows:
                for bay in range(1, MAX_BAYS + 1):
                    for sub_slot in allowed_slots:
                        for tier in range(PREFERRED_STACK_HEIGHT + 1, MAX_TIERS + 1):
                            if self._is_position_available(
                                zone, row, bay, tier, sub_slot
                            ):
                                if self._has_support_below(
                                    zone, row, bay, tier, sub_slot
                                ):
                                    return (zone, row, bay, tier, sub_slot)

        return None

    def _get_zones_by_availability(self) -> list:
        """Get zones ordered by available ground-level slots (most available first)."""
        zone_usage = (
            ContainerPosition.objects.filter(tier=1)
            .values("zone")
            .annotate(used=Count("id"))
        )
        usage_map = {item["zone"]: item["used"] for item in zone_usage}

        # Sort zones by available ground slots
        return sorted(
            ZONES,
            key=lambda z: usage_map.get(z, 0),
        )

    def _find_alternatives(
        self,
        primary: tuple,
        container_size: str = "20ft",
        limit: int = 3,
    ) -> list:
        """
        Find alternative positions excluding the primary suggestion.

        Uses same size-aware row segregation and sub-slot logic as main algorithm.
        """
        alternatives = []
        primary_zone, primary_row, primary_bay, primary_tier, primary_slot = primary
        allowed_rows = self._get_rows_for_size(container_size)
        allowed_slots = self._get_sub_slots_for_size(container_size)

        # Look for positions in same zone first, then other zones
        zones = [primary_zone] + [z for z in ZONES if z != primary_zone]

        for zone in zones:
            for row in allowed_rows:
                for bay in range(1, MAX_BAYS + 1):
                    for sub_slot in allowed_slots:
                        for tier in range(1, MAX_TIERS + 1):
                            if (zone, row, bay, tier, sub_slot) == primary:
                                continue
                            if self._is_position_available(
                                zone, row, bay, tier, sub_slot
                            ):
                                if tier == 1 or self._has_support_below(
                                    zone, row, bay, tier, sub_slot
                                ):
                                    alternatives.append(
                                        (zone, row, bay, tier, sub_slot)
                                    )
                                    if len(alternatives) >= limit:
                                        return alternatives

        return alternatives

    def _build_suggestion_reason(
        self,
        zone: str,
        row: int,
        tier: int,
        container_size: str,
        zone_preference: Optional[str],
    ) -> str:
        """Build human-readable reason for suggestion."""
        # Determine row area name
        if container_size in ("40ft", "45ft"):
            area_name = "зона 40ft (ряды 1-5)"
        else:
            area_name = "зона 20ft (ряды 6-10)"

        if zone_preference:
            if tier == 1:
                return f"Ближайшая позиция в {area_name}, ряд {row}"
            return f"Позиция в {area_name}, ряд {row} (ярус {tier})"
        else:
            if tier == 1:
                return f"Оптимальная позиция в {area_name}, ряд {row} (консолидация)"
            return f"Позиция в {area_name}, ряд {row} (ярус {tier}, консолидация)"

    def _is_position_available(
        self,
        zone: str,
        row: int,
        bay: int,
        tier: int,
        sub_slot: str = "A",
    ) -> bool:
        """Check if a position is available (including sub_slot)."""
        return not ContainerPosition.objects.filter(
            zone=zone,
            row=row,
            bay=bay,
            tier=tier,
            sub_slot=sub_slot,
        ).exists()

    def _has_support_below(
        self,
        zone: str,
        row: int,
        bay: int,
        tier: int,
        sub_slot: str = "A",
    ) -> bool:
        """Check if there's a container below to support this tier."""
        if tier == 1:
            return True  # Ground level doesn't need support
        return ContainerPosition.objects.filter(
            zone=zone,
            row=row,
            bay=bay,
            tier=tier - 1,
            sub_slot=sub_slot,
        ).exists()

    def _get_container_size(self, iso_type: str) -> str:
        """
        Get container size from ISO type code.

        ISO type codes:
        - First character: 2 = 20ft, 4 = 40ft, L/9 = 45ft
        - Second character: 2/3 = standard height, 5/9 = high cube

        Examples: 22G1 = 20ft standard, 45G1 = 40ft HC, 22R1 = 20ft reefer
        """
        if not iso_type:
            return "20ft"
        first_char = iso_type[0] if iso_type else "2"
        if first_char == "2":
            return "20ft"
        elif first_char == "4":
            return "40ft"
        elif first_char in ("L", "9"):
            return "45ft"
        return "20ft"

    def _get_container_below(
        self,
        zone: str,
        row: int,
        bay: int,
        tier: int,
    ) -> ContainerPosition | None:
        """Get the container position directly below this tier."""
        if tier == 1:
            return None
        return (
            ContainerPosition.objects.filter(
                zone=zone,
                row=row,
                bay=bay,
                tier=tier - 1,
            )
            .select_related("container_entry__container", "container_entry")
            .first()
        )

    def _validate_row_segregation(
        self,
        iso_type: str,
        zone: str,
        row: int,
        bay: int,
        tier: int,
    ) -> None:
        """
        Validate that container is placed in the correct row area for its size.

        TOS Rule: Row segregation prevents mixing 20ft and 40ft containers
        - Rows 1-5: 40ft containers only
        - Rows 6-10: 20ft containers only

        This prevents corner post misalignment issues when stacking.
        """
        container_size = self._get_container_size(iso_type)
        allowed_rows = self._get_rows_for_size(container_size)
        coordinate = format_coordinate(zone, row, bay, tier)

        if row not in allowed_rows:
            raise RowSegregationError(coordinate, container_size, allowed_rows)

    def _validate_size_compatibility(
        self,
        top_iso_type: str,
        zone: str,
        row: int,
        bay: int,
        tier: int,
    ) -> None:
        """
        Validate that container size is compatible with container below.

        ISO Standard Rules:
        - 40ft container can only be placed on another 40ft container
        - 20ft container can be placed on either 20ft or 40ft
        - Never place 40ft directly on single 20ft (corner posts don't align)
        """
        if tier == 1:
            return  # No validation needed for ground level

        position_below = self._get_container_below(zone, row, bay, tier)
        if not position_below:
            return  # No container below (will fail support check anyway)

        top_size = self._get_container_size(top_iso_type)
        bottom_size = self._get_container_size(
            position_below.container_entry.container.iso_type
        )
        coordinate = format_coordinate(zone, row, bay, tier)

        # Rule: 40ft on 20ft is NOT allowed (corner posts don't align)
        if top_size in ("40ft", "45ft") and bottom_size == "20ft":
            raise SizeCompatibilityError(coordinate, top_size, bottom_size)

    def _validate_weight_distribution(
        self,
        top_status: str,
        zone: str,
        row: int,
        bay: int,
        tier: int,
    ) -> None:
        """
        Validate that weight distribution follows ISO guidelines.

        ISO Standard Rule:
        - Laden (heavy) containers must be at bottom
        - Empty (light) containers must be at top
        - Never place laden container on top of empty container
        """
        if tier == 1:
            return  # No validation needed for ground level

        position_below = self._get_container_below(zone, row, bay, tier)
        if not position_below:
            return  # No container below

        bottom_status = position_below.container_entry.status
        coordinate = format_coordinate(zone, row, bay, tier)

        # Rule: LADEN on top of EMPTY is NOT allowed
        if top_status == "LADEN" and bottom_status == "EMPTY":
            raise WeightDistributionError(coordinate)

    @transaction.atomic
    def assign_position(
        self,
        container_entry_id: int,
        zone: str,
        row: int,
        bay: int,
        tier: int,
        sub_slot: str = "A",
        auto_assigned: bool = False,
    ) -> ContainerPosition:
        """
        Assign a container to a specific position.

        Args:
            container_entry_id: ContainerEntry to place
            zone: Zone code (A-E)
            row: Row number (1-10)
            bay: Bay number (1-10)
            tier: Tier/level (1-4)
            sub_slot: Sub-slot within bay (A or B, for 20ft containers)
            auto_assigned: Whether this was auto-suggested

        Returns:
            Created ContainerPosition

        Raises:
            PositionOccupiedError: If position is taken
            NoSupportError: If tier > 1 and no support below
            ContainerAlreadyPlacedError: If container already placed
        """
        # Validate inputs
        self._validate_coordinates(zone, row, bay, tier, sub_slot)

        # Get container entry
        try:
            entry = ContainerEntry.objects.select_related("container", "position").get(
                id=container_entry_id
            )
        except ContainerEntry.DoesNotExist:
            raise BusinessLogicError(
                message=f"Запись контейнера с ID {container_entry_id} не найдена",
                error_code="CONTAINER_ENTRY_NOT_FOUND",
            )

        # Check if already placed
        if hasattr(entry, "position") and entry.position:
            raise ContainerAlreadyPlacedError(
                entry.container.container_number,
                entry.position.coordinate_string,
            )

        # Validate sub_slot based on container size
        container_size = self._get_container_size(entry.container.iso_type)
        if container_size in ("40ft", "45ft") and sub_slot != "A":
            raise BusinessLogicError(
                message="40ft/45ft контейнеры должны использовать слот A (занимают весь отсек)",
                error_code="INVALID_SUB_SLOT_FOR_SIZE",
            )

        # Check stacking rules for tier > 1
        coordinate = format_coordinate(zone, row, bay, tier, sub_slot)
        if tier > 1 and not self._has_support_below(zone, row, bay, tier, sub_slot):
            raise NoSupportError(coordinate)

        # TOS Standard Rules
        # Rule 0: Row segregation (40ft in rows 1-5, 20ft in rows 6-10)
        self._validate_row_segregation(entry.container.iso_type, zone, row, bay, tier)

        # Rule 1: Size compatibility (40ft cannot be placed on 20ft)
        self._validate_size_compatibility(
            entry.container.iso_type, zone, row, bay, tier
        )

        # Rule 2: Weight distribution (laden cannot be placed on empty)
        self._validate_weight_distribution(entry.status, zone, row, bay, tier)

        # Create position
        try:
            position = ContainerPosition.objects.create(
                container_entry=entry,
                zone=zone,
                row=row,
                bay=bay,
                tier=tier,
                sub_slot=sub_slot,
                auto_assigned=auto_assigned,
            )
        except IntegrityError:
            raise PositionOccupiedError(coordinate)

        # Update ContainerEntry.location field for backward compatibility
        entry.location = position.coordinate_string
        entry.save(update_fields=["location"])

        self.logger.info(
            f"Assigned container {entry.container.container_number} "
            f"to position {position.coordinate_string}"
        )

        return position

    def _validate_coordinates(
        self,
        zone: str,
        row: int,
        bay: int,
        tier: int,
        sub_slot: str = "A",
    ) -> None:
        """Validate coordinate values are within bounds."""
        if sub_slot not in ("A", "B"):
            raise BusinessLogicError(
                message=f"Недопустимый слот: {sub_slot}. Допустимые: A, B",
                error_code="INVALID_SUB_SLOT",
            )
        if zone not in ZONES:
            raise BusinessLogicError(
                message=f"Недопустимая зона: {zone}. Допустимые: {', '.join(ZONES)}",
                error_code="INVALID_ZONE",
            )
        if not 1 <= row <= MAX_ROWS:
            raise BusinessLogicError(
                message=f"Недопустимый ряд: {row}. Допустимые: 1-{MAX_ROWS}",
                error_code="INVALID_ROW",
            )
        if not 1 <= bay <= MAX_BAYS:
            raise BusinessLogicError(
                message=f"Недопустимый отсек: {bay}. Допустимые: 1-{MAX_BAYS}",
                error_code="INVALID_BAY",
            )
        if not 1 <= tier <= MAX_TIERS:
            raise BusinessLogicError(
                message=f"Недопустимый ярус: {tier}. Допустимые: 1-{MAX_TIERS}",
                error_code="INVALID_TIER",
            )

    @transaction.atomic
    def move_container(
        self,
        position_id: int,
        new_zone: str,
        new_row: int,
        new_bay: int,
        new_tier: int,
    ) -> ContainerPosition:
        """
        Move a container to a new position.

        Args:
            position_id: ContainerPosition to move
            new_zone: New zone code
            new_row: New row number
            new_bay: New bay number
            new_tier: New tier level

        Returns:
            Updated ContainerPosition
        """
        self._validate_coordinates(new_zone, new_row, new_bay, new_tier)

        try:
            position = ContainerPosition.objects.select_related(
                "container_entry__container"
            ).get(id=position_id)
        except ContainerPosition.DoesNotExist:
            raise BusinessLogicError(
                message=f"Позиция с ID {position_id} не найдена",
                error_code="POSITION_NOT_FOUND",
            )

        # Check if new position is available (ignore current position)
        new_coordinate = format_coordinate(new_zone, new_row, new_bay, new_tier)
        if (
            ContainerPosition.objects.filter(
                zone=new_zone,
                row=new_row,
                bay=new_bay,
                tier=new_tier,
            )
            .exclude(id=position_id)
            .exists()
        ):
            raise PositionOccupiedError(new_coordinate)

        # Check stacking rules
        if new_tier > 1 and not self._has_support_below(
            new_zone, new_row, new_bay, new_tier
        ):
            raise NoSupportError(new_coordinate)

        # TOS Standard Rules
        # Rule 0: Row segregation (40ft in rows 1-5, 20ft in rows 6-10)
        self._validate_row_segregation(
            position.container_entry.container.iso_type,
            new_zone,
            new_row,
            new_bay,
            new_tier,
        )

        # Rule 1: Size compatibility (40ft cannot be placed on 20ft)
        self._validate_size_compatibility(
            position.container_entry.container.iso_type,
            new_zone,
            new_row,
            new_bay,
            new_tier,
        )

        # Rule 2: Weight distribution (laden cannot be placed on empty)
        self._validate_weight_distribution(
            position.container_entry.status,
            new_zone,
            new_row,
            new_bay,
            new_tier,
        )

        old_coordinate = position.coordinate_string

        # Update position
        position.zone = new_zone
        position.row = new_row
        position.bay = new_bay
        position.tier = new_tier
        position.save()

        # Update ContainerEntry.location
        position.container_entry.location = position.coordinate_string
        position.container_entry.save(update_fields=["location"])

        self.logger.info(
            f"Moved container {position.container_entry.container.container_number} "
            f"from {old_coordinate} to {position.coordinate_string}"
        )

        return position

    @transaction.atomic
    def remove_position(self, position_id: int) -> None:
        """
        Remove a container from its position (e.g., on exit).

        Args:
            position_id: ContainerPosition to remove
        """
        try:
            position = ContainerPosition.objects.select_related("container_entry").get(
                id=position_id
            )
        except ContainerPosition.DoesNotExist:
            raise BusinessLogicError(
                message=f"Позиция с ID {position_id} не найдена",
                error_code="POSITION_NOT_FOUND",
            )

        container_number = position.container_entry.container.container_number
        coordinate = position.coordinate_string

        # Clear location on entry
        position.container_entry.location = ""
        position.container_entry.save(update_fields=["location"])

        # Delete position
        position.delete()

        self.logger.info(
            f"Removed container {container_number} from position {coordinate}"
        )

    def get_available_positions(
        self,
        zone: Optional[str] = None,
        tier: Optional[int] = None,
        limit: int = 50,
    ) -> list:
        """
        Get list of available positions with optional filters.

        Args:
            zone: Filter by zone (optional)
            tier: Filter by tier (optional)
            limit: Max results to return

        Returns:
            List of available positions
        """
        # Get all occupied coordinates
        occupied = set(
            ContainerPosition.objects.values_list("zone", "row", "bay", "tier")
        )

        available = []
        zones_to_check = [zone] if zone else ZONES
        tiers_to_check = [tier] if tier else range(1, MAX_TIERS + 1)

        for z in zones_to_check:
            for t in tiers_to_check:
                for r in range(1, MAX_ROWS + 1):
                    for b in range(1, MAX_BAYS + 1):
                        if (z, r, b, t) not in occupied:
                            # Check stacking rules
                            if t == 1 or (z, r, b, t - 1) in occupied:
                                available.append(
                                    {
                                        "zone": z,
                                        "row": r,
                                        "bay": b,
                                        "tier": t,
                                        "coordinate": format_coordinate(z, r, b, t),
                                    }
                                )
                                if len(available) >= limit:
                                    return available

        return available

    def get_unplaced_containers(self) -> list:
        """
        Get containers currently on terminal without a position AND without active work orders.

        Containers with pending/assigned/in-progress work orders are excluded because
        they will be shown in the 3D view at their target position with "pending" status.

        Returns:
            List of ContainerEntry dicts without positions and without active work orders
        """
        # Get IDs of containers with active work orders
        active_work_order_statuses = ["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"]
        entries_with_active_orders = WorkOrder.objects.filter(
            status__in=active_work_order_statuses
        ).values_list("container_entry_id", flat=True)

        entries = ContainerEntry.objects.filter(
            exit_date__isnull=True,
            position__isnull=True,
        ).exclude(
            id__in=entries_with_active_orders
        ).select_related("container", "company")

        return [
            {
                "id": entry.id,
                "container_number": entry.container.container_number,
                "iso_type": entry.container.iso_type,
                "status": entry.status,
                "entry_time": entry.entry_time.isoformat(),
                "dwell_time_days": entry.dwell_time_days,
                "company_name": (
                    entry.company.name if entry.company else entry.client_name
                ),
            }
            for entry in entries
        ]
