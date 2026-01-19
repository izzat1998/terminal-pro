"""
Work order serializers.

Handles work order CRUD operations for container placement tasks.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


def get_container_size_from_iso(iso_type: str) -> str:
    """Get container size (20, 40, or 45) from ISO type code."""
    if not iso_type:
        return "20"
    first_char = iso_type[0]
    if first_char == "4":
        return "40"
    if first_char in ("L", "9"):
        return "45"
    return "20"


class WorkOrderContainerSerializer(serializers.Serializer):
    """
    Nested container info for work order responses.
    """

    id = serializers.IntegerField()
    number = serializers.CharField(source="container.container_number")
    iso_type = serializers.CharField(source="container.iso_type")
    size = serializers.SerializerMethodField()
    load_status = serializers.CharField(source="status")
    weight_kg = serializers.DecimalField(
        source="cargo_weight",
        max_digits=10,
        decimal_places=2,
        allow_null=True,
    )

    def get_size(self, obj):
        """Get container size from ISO type (20, 40, or 45)."""
        iso_type = obj.container.iso_type if obj.container else ""
        return get_container_size_from_iso(iso_type)


class WorkOrderTargetLocationSerializer(serializers.Serializer):
    """
    Nested target location for work order responses.
    """

    zone = serializers.CharField()
    row = serializers.IntegerField()
    bay = serializers.IntegerField()
    tier = serializers.IntegerField()
    sub_slot = serializers.CharField()
    display_code = serializers.CharField()


class WorkOrderVehicleSerializer(serializers.Serializer):
    """
    Nested vehicle info for work order responses.
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    vehicle_type = serializers.CharField()
    vehicle_type_display = serializers.SerializerMethodField()

    def get_vehicle_type_display(self, obj):
        return obj.get_vehicle_type_display() if obj else None


class TerminalVehicleOperatorSerializer(serializers.Serializer):
    """
    Nested operator info for terminal vehicle responses.
    """

    id = serializers.IntegerField()
    full_name = serializers.CharField()


class TerminalVehicleSerializer(serializers.ModelSerializer):
    """
    Serializer for TerminalVehicle model.
    Used for listing terminal vehicles with operator info.
    """

    from ..models import TerminalVehicle

    vehicle_type_display = serializers.SerializerMethodField()
    operator = serializers.SerializerMethodField()

    class Meta:
        from ..models import TerminalVehicle

        model = TerminalVehicle
        fields = [
            "id",
            "name",
            "vehicle_type",
            "vehicle_type_display",
            "license_plate",
            "is_active",
            "operator",
        ]

    def get_vehicle_type_display(self, obj):
        return obj.get_vehicle_type_display()

    @extend_schema_field({"type": "object", "nullable": True})
    def get_operator(self, obj):
        """Return operator info with id and full_name."""
        if obj.operator:
            return {
                "id": obj.operator.id,
                "full_name": obj.operator.full_name or obj.operator.username,
            }
        return None


class TerminalVehicleWriteSerializer(serializers.Serializer):
    """
    Serializer for creating/updating terminal vehicles.
    """

    name = serializers.CharField(
        max_length=100,
        help_text="Название/номер техники (например, RS-01, Погрузчик-3)",
    )
    vehicle_type = serializers.ChoiceField(
        choices=[
            ("REACH_STACKER", "Ричстакер"),
            ("FORKLIFT", "Погрузчик"),
            ("YARD_TRUCK", "Тягач"),
            ("RTG_CRANE", "Козловой кран (RTG)"),
        ],
        help_text="Тип техники",
    )
    license_plate = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
        help_text="Госномер (если есть)",
    )
    operator_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID оператора (менеджера)",
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Активна ли техника",
    )


class WorkOrderSerializer(serializers.ModelSerializer):
    """
    Full serializer for WorkOrder model.
    Used for detail views and responses.
    """

    from ..models import WorkOrder

    container = serializers.SerializerMethodField()
    target_location = serializers.SerializerMethodField()
    assigned_to_vehicle = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()

    class Meta:
        from ..models import WorkOrder

        model = WorkOrder
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "container",
            "target_location",
            "assigned_to_vehicle",
            "created_at",
            "completed_at",
            "notes",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "created_at",
            "completed_at",
        ]

    @extend_schema_field({"type": "object"})
    def get_container(self, obj):
        return WorkOrderContainerSerializer(obj.container_entry).data

    @extend_schema_field({"type": "object"})
    def get_target_location(self, obj):
        return {
            "zone": obj.target_zone,
            "row": obj.target_row,
            "bay": obj.target_bay,
            "tier": obj.target_tier,
            "sub_slot": obj.target_sub_slot,
            "display_code": obj.target_coordinate_string,
        }

    @extend_schema_field({"type": "object", "nullable": True})
    def get_assigned_to_vehicle(self, obj):
        if obj.assigned_to_vehicle:
            return {
                "id": obj.assigned_to_vehicle.id,
                "name": obj.assigned_to_vehicle.name,
                "vehicle_type": obj.assigned_to_vehicle.vehicle_type,
                "vehicle_type_display": obj.assigned_to_vehicle.get_vehicle_type_display(),
            }
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_status_display(self, obj):
        return obj.get_status_display()

    @extend_schema_field(OpenApiTypes.STR)
    def get_priority_display(self, obj):
        return obj.get_priority_display()


class WorkOrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for work order list views.
    """

    from ..models import WorkOrder

    container_number = serializers.CharField(
        source="container_entry.container.container_number",
        read_only=True,
    )
    container_size = serializers.SerializerMethodField()
    target_coordinate = serializers.CharField(
        source="target_coordinate_string",
        read_only=True,
    )
    assigned_vehicle_name = serializers.SerializerMethodField()
    assigned_to_vehicle = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()

    class Meta:
        from ..models import WorkOrder

        model = WorkOrder
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "container_number",
            "container_size",
            "target_coordinate",
            "assigned_vehicle_name",
            "assigned_to_vehicle",
            "created_at",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_container_size(self, obj):
        iso_type = obj.container_entry.container.iso_type if obj.container_entry else ""
        return get_container_size_from_iso(iso_type)

    @extend_schema_field({"type": "string", "nullable": True})
    def get_assigned_vehicle_name(self, obj):
        return obj.assigned_to_vehicle.name if obj.assigned_to_vehicle else None

    @extend_schema_field({"type": "object", "nullable": True})
    def get_assigned_to_vehicle(self, obj):
        """Return full vehicle object for frontend compatibility."""
        if obj.assigned_to_vehicle:
            return {
                "id": obj.assigned_to_vehicle.id,
                "name": obj.assigned_to_vehicle.name,
                "vehicle_type": obj.assigned_to_vehicle.vehicle_type,
                "vehicle_type_display": obj.assigned_to_vehicle.get_vehicle_type_display(),
            }
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_status_display(self, obj):
        return obj.get_status_display()

    @extend_schema_field(OpenApiTypes.STR)
    def get_priority_display(self, obj):
        return obj.get_priority_display()


class WorkOrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating work orders.
    """

    container_entry_id = serializers.IntegerField(
        help_text="Container entry to be placed",
    )
    zone = serializers.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E")],
        required=False,
        allow_null=True,
        help_text="Target zone (optional, auto-suggested if not provided)",
    )
    row = serializers.IntegerField(
        min_value=1,
        max_value=10,
        required=False,
        allow_null=True,
        help_text="Target row (optional)",
    )
    bay = serializers.IntegerField(
        min_value=1,
        max_value=10,
        required=False,
        allow_null=True,
        help_text="Target bay (optional)",
    )
    tier = serializers.IntegerField(
        min_value=1,
        max_value=4,
        required=False,
        allow_null=True,
        help_text="Target tier (optional)",
    )
    sub_slot = serializers.ChoiceField(
        choices=[("A", "Slot A"), ("B", "Slot B")],
        required=False,
        default="A",
        help_text="Sub-slot for 20ft containers",
    )
    priority = serializers.ChoiceField(
        choices=[
            ("LOW", "Low"),
            ("MEDIUM", "Medium"),
            ("HIGH", "High"),
            ("URGENT", "Urgent"),
        ],
        required=False,
        default="MEDIUM",
        help_text="Order priority",
    )
    assigned_to_vehicle_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Terminal vehicle ID to assign (optional)",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Additional notes",
    )


class WorkOrderAssignSerializer(serializers.Serializer):
    """
    Serializer for assigning work order to terminal vehicle.
    """

    vehicle_id = serializers.IntegerField(
        help_text="Terminal vehicle ID to assign",
    )


class TerminalVehicleStatusSerializer(serializers.Serializer):
    """
    Serializer for terminal vehicles with work status.

    Used for sidebar display showing vehicles with operators and current work.
    Computes status from: is_active + operator + pending work orders.

    Statuses:
    - available: Active, has operator, no pending work
    - working: Has pending work order
    - offline: Inactive or no operator assigned
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    vehicle_type = serializers.CharField()
    vehicle_type_display = serializers.SerializerMethodField()
    operator_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    current_task = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_vehicle_type_display(self, obj):
        """Return human-readable vehicle type."""
        return obj.get_vehicle_type_display()

    @extend_schema_field({"type": "string", "nullable": True})
    def get_operator_name(self, obj):
        """Return operator's full name or None."""
        if obj.operator:
            return obj.operator.full_name or obj.operator.username
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, obj):
        """Compute vehicle status."""
        if not obj.is_active or not obj.operator:
            return "offline"

        # Check for assigned pending work orders
        has_active_work = obj.work_orders.filter(status="PENDING").exists()

        if has_active_work:
            return "working"

        return "available"

    @extend_schema_field({"type": "object", "nullable": True})
    def get_current_task(self, obj):
        """Return current task info if vehicle has assigned work."""
        active_order = (
            obj.work_orders.filter(status="PENDING")
            .select_related("container_entry__container")
            .order_by("-priority", "-created_at")
            .first()
        )

        if active_order:
            return {
                "container_number": active_order.container_entry.container.container_number,
                "target_coordinate": active_order.target_coordinate_string,
            }

        return None
