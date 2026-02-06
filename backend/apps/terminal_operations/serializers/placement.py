"""
Placement serializers.

Handles 3D terminal container placement operations.
"""

from rest_framework import serializers


class PositionSerializer(serializers.Serializer):
    """
    Serializer for position coordinates (used in requests and responses).
    """

    zone = serializers.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E")],
        help_text="Terminal zone (A-E)",
    )
    row = serializers.IntegerField(
        min_value=1,
        max_value=10,
        help_text="Row number (1-10)",
    )
    bay = serializers.IntegerField(
        min_value=1,
        max_value=10,
        help_text="Bay number (1-10)",
    )
    tier = serializers.IntegerField(
        min_value=1,
        max_value=4,
        help_text="Tier/level (1-4)",
    )
    coordinate = serializers.CharField(
        read_only=True,
        help_text="Formatted coordinate (e.g., A-R03-B15-T2)",
    )


class ContainerPositionSerializer(serializers.ModelSerializer):
    """
    Serializer for ContainerPosition model.
    """

    from ..models import ContainerPosition

    coordinate = serializers.CharField(
        source="coordinate_string",
        read_only=True,
    )
    container_number = serializers.CharField(
        source="container_entry.container.container_number",
        read_only=True,
    )

    class Meta:
        from ..models import ContainerPosition

        model = ContainerPosition
        fields = [
            "id",
            "container_entry",
            "container_number",
            "zone",
            "row",
            "bay",
            "tier",
            "sub_slot",
            "coordinate",
            "auto_assigned",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "container_number",
            "coordinate",
            "created_at",
            "updated_at",
        ]


class PlacementLayoutSerializer(serializers.Serializer):
    """
    Serializer for 3D terminal layout response.
    """

    zones = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of zone codes (A-E)",
    )
    dimensions = serializers.DictField(
        help_text="Terminal dimensions (max_rows, max_bays, max_tiers)",
    )
    containers = serializers.ListField(
        help_text="List of positioned containers with coordinates",
    )
    stats = serializers.DictField(
        help_text="Occupancy statistics",
    )


class PlacementSuggestRequestSerializer(serializers.Serializer):
    """
    Request serializer for auto-suggest position.
    """

    container_entry_id = serializers.IntegerField(
        help_text="ID of the container entry to place",
    )
    zone_preference = serializers.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E")],
        required=False,
        allow_null=True,
        help_text="Preferred zone (optional)",
    )


class PlacementSuggestResponseSerializer(serializers.Serializer):
    """
    Response serializer for auto-suggest position.
    """

    suggested_position = PositionSerializer()
    reason = serializers.CharField(help_text="Human-readable reason for suggestion")
    alternatives = serializers.ListField(
        child=PositionSerializer(),
        help_text="Alternative positions",
    )


class PlacementAssignRequestSerializer(serializers.Serializer):
    """
    Request serializer for assigning position to container.
    """

    container_entry_id = serializers.IntegerField(
        help_text="ID of the container entry to place",
    )
    position = PositionSerializer(
        help_text="Target position coordinates",
    )


class PlacementMoveRequestSerializer(serializers.Serializer):
    """
    Request serializer for moving container to new position.
    """

    new_position = PositionSerializer(
        help_text="New position coordinates",
    )


class PlacementAvailableRequestSerializer(serializers.Serializer):
    """
    Query params serializer for available positions.
    """

    zone = serializers.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E")],
        required=False,
        allow_null=True,
        help_text="Filter by zone (optional)",
    )
    tier = serializers.IntegerField(
        min_value=1,
        max_value=4,
        required=False,
        allow_null=True,
        help_text="Filter by tier (optional)",
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
        default=50,
        help_text="Max positions to return (default 50)",
    )


class YardSlotContainerEntrySerializer(serializers.Serializer):
    """Lightweight serializer for yard slot occupant data (3D rendering)."""

    id = serializers.IntegerField()
    container_number = serializers.CharField()
    iso_type = serializers.CharField()
    status = serializers.CharField()
    is_hazmat = serializers.BooleanField()
    imo_class = serializers.CharField(allow_null=True)
    priority = serializers.CharField()
    company_name = serializers.CharField(allow_null=True)
    dwell_time_days = serializers.IntegerField()
    entry_time = serializers.DateTimeField()
    cargo_name = serializers.CharField()


class YardSlotSerializer(serializers.ModelSerializer):
    """
    Yard slot with DXF coordinates and optional occupant data.
    Used by the unified 3D yard view.
    """

    from ..models import ContainerPosition

    container_entry = serializers.SerializerMethodField()

    class Meta:
        from ..models import ContainerPosition

        model = ContainerPosition
        fields = [
            "id",
            "zone",
            "row",
            "bay",
            "tier",
            "sub_slot",
            "dxf_x",
            "dxf_y",
            "rotation",
            "container_size",
            "container_entry",
        ]
        read_only_fields = fields

    def get_container_entry(self, obj):
        if not obj.container_entry:
            return None
        entry = obj.container_entry
        return {
            "id": entry.id,
            "container_number": entry.container.container_number,
            "iso_type": entry.container.iso_type,
            "status": entry.status,
            "is_hazmat": entry.is_hazmat,
            "imo_class": entry.imo_class,
            "priority": entry.priority,
            "company_name": entry.company.name if entry.company else (entry.client_name or None),
            "dwell_time_days": entry.dwell_time_days,
            "entry_time": entry.entry_time,
            "cargo_name": entry.cargo_name,
        }


class UnplacedContainerSerializer(serializers.Serializer):
    """
    Serializer for containers without assigned positions.
    """

    id = serializers.IntegerField(help_text="Container entry ID")
    container_number = serializers.CharField(help_text="Container number")
    iso_type = serializers.CharField(help_text="ISO container type")
    status = serializers.CharField(help_text="LADEN or EMPTY")
    entry_time = serializers.DateTimeField(help_text="Entry timestamp")
    dwell_time_days = serializers.IntegerField(help_text="Days on terminal")
    company_name = serializers.CharField(help_text="Company or client name")
