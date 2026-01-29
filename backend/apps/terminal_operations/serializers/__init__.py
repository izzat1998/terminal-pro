"""
Terminal Operations Serializers Package.

Re-exports all serializers for backward compatibility.
Import from submodules for cleaner, more explicit imports:
    from apps.terminal_operations.serializers.containers import ContainerEntrySerializer
    from apps.terminal_operations.serializers.preorders import PreOrderSerializer
"""

# Base/shared serializers
from .base import (
    ContainerNestedSerializer,
    ContainerOwnerSerializer,
    CraneOperationSerializer,
    CraneOperationWriteSerializer,
    UserNestedSerializer,
)

# Container entry serializers
from .containers import (
    ContainerEntryImportSerializer,
    ContainerEntrySerializer,
    ContainerEntryWithImagesSerializer,
    PlateRecognitionRequestSerializer,
    PlateRecognitionResponseSerializer,
    VehicleDetectionResponseSerializer,
)

# Placement serializers
from .placement import (
    ContainerPositionSerializer,
    PlacementAssignRequestSerializer,
    PlacementAvailableRequestSerializer,
    PlacementLayoutSerializer,
    PlacementMoveRequestSerializer,
    PlacementSuggestRequestSerializer,
    PlacementSuggestResponseSerializer,
    PositionSerializer,
    UnplacedContainerSerializer,
    YardSlotContainerEntrySerializer,
    YardSlotSerializer,
)

# PreOrder serializers
from .preorders import (
    ContainerEntryNestedSerializer,
    CustomerNestedSerializer,
    PreOrderListSerializer,
    PreOrderSerializer,
    VehicleEntryNestedSerializer,
)

# Vehicle serializers
from .vehicles import (
    VehicleEntryCreateSerializer,
    VehicleEntryListSerializer,
    VehicleEntrySerializer,
    VehicleEntryUpdateStatusSerializer,
)

# Work order serializers
from .work_orders import (
    TerminalVehicleOperatorSerializer,
    TerminalVehicleSerializer,
    TerminalVehicleStatusSerializer,
    TerminalVehicleWriteSerializer,
    WorkOrderAssignSerializer,
    WorkOrderContainerSerializer,
    WorkOrderCreateSerializer,
    WorkOrderListSerializer,
    WorkOrderSerializer,
    WorkOrderTargetLocationSerializer,
    WorkOrderVehicleSerializer,
    get_container_size_from_iso,
)

# Event serializers
from .events import (
    ContainerEventSerializer,
    ContainerTimelineSerializer,
    EventPerformerSerializer,
)


__all__ = [
    # Base
    "ContainerOwnerSerializer",
    "ContainerNestedSerializer",
    "UserNestedSerializer",
    "CraneOperationSerializer",
    "CraneOperationWriteSerializer",
    # Containers
    "ContainerEntrySerializer",
    "ContainerEntryWithImagesSerializer",
    "ContainerEntryImportSerializer",
    "PlateRecognitionRequestSerializer",
    "PlateRecognitionResponseSerializer",
    "VehicleDetectionResponseSerializer",
    # PreOrders
    "VehicleEntryNestedSerializer",
    "ContainerEntryNestedSerializer",
    "CustomerNestedSerializer",
    "PreOrderSerializer",
    "PreOrderListSerializer",
    # Vehicles
    "VehicleEntrySerializer",
    "VehicleEntryListSerializer",
    "VehicleEntryCreateSerializer",
    "VehicleEntryUpdateStatusSerializer",
    # Placement
    "PositionSerializer",
    "ContainerPositionSerializer",
    "PlacementLayoutSerializer",
    "PlacementSuggestRequestSerializer",
    "PlacementSuggestResponseSerializer",
    "PlacementAssignRequestSerializer",
    "PlacementMoveRequestSerializer",
    "PlacementAvailableRequestSerializer",
    "UnplacedContainerSerializer",
    "YardSlotContainerEntrySerializer",
    "YardSlotSerializer",
    # Work Orders
    "get_container_size_from_iso",
    "WorkOrderContainerSerializer",
    "WorkOrderTargetLocationSerializer",
    "WorkOrderVehicleSerializer",
    "TerminalVehicleOperatorSerializer",
    "TerminalVehicleSerializer",
    "TerminalVehicleStatusSerializer",
    "TerminalVehicleWriteSerializer",
    "WorkOrderSerializer",
    "WorkOrderListSerializer",
    "WorkOrderCreateSerializer",
    "WorkOrderAssignSerializer",
    # Events
    "EventPerformerSerializer",
    "ContainerEventSerializer",
    "ContainerTimelineSerializer",
]
