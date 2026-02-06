"""
VehicleEntry serializers.

Handles vehicle entry/exit operations for terminal gate management.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.vehicles.models import VehicleEntry


class VehicleEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for VehicleEntry model (from vehicles app).
    Used for detailed view of vehicle entries.
    """

    status_display = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()
    vehicle_type_display = serializers.SerializerMethodField()
    pre_orders_count = serializers.SerializerMethodField()

    class Meta:
        model = VehicleEntry
        fields = (
            "id",
            "license_plate",
            "status",
            "status_display",
            "vehicle_type",
            "vehicle_type_display",
            "customer",
            "customer_name",
            "recorded_by",
            "recorded_by_name",
            "entry_time",
            "exit_time",
            "destination",
            "pre_orders_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    @extend_schema_field(OpenApiTypes.STR)
    def get_status_display(self, obj):
        """Get human-readable status."""
        return obj.get_status_display()

    @extend_schema_field({"type": "string", "nullable": True})
    def get_customer_name(self, obj):
        """Get customer's display name."""
        return obj.customer.full_name if obj.customer else None

    @extend_schema_field({"type": "string", "nullable": True})
    def get_recorded_by_name(self, obj):
        """Get recorder's display name."""
        return obj.recorded_by.full_name if obj.recorded_by else None

    @extend_schema_field({"type": "string", "nullable": True})
    def get_vehicle_type_display(self, obj):
        """Get human-readable vehicle type."""
        return obj.get_vehicle_type_display() if obj.vehicle_type else None

    @extend_schema_field(OpenApiTypes.INT)
    def get_pre_orders_count(self, obj):
        """Get count of pre-orders linked to this vehicle entry."""
        return obj.pre_orders.count() if hasattr(obj, "pre_orders") else 0


class VehicleEntryListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for VehicleEntry list views.
    """

    status_display = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    vehicle_type_display = serializers.SerializerMethodField()

    class Meta:
        model = VehicleEntry
        fields = (
            "id",
            "license_plate",
            "status",
            "status_display",
            "vehicle_type",
            "vehicle_type_display",
            "customer_name",
            "entry_time",
            "created_at",
        )
        read_only_fields = "__all__"

    @extend_schema_field(OpenApiTypes.STR)
    def get_status_display(self, obj):
        return obj.get_status_display()

    @extend_schema_field({"type": "string", "nullable": True})
    def get_customer_name(self, obj):
        return obj.customer.full_name if obj.customer else None

    @extend_schema_field({"type": "string", "nullable": True})
    def get_vehicle_type_display(self, obj):
        return obj.get_vehicle_type_display() if obj.vehicle_type else None


class VehicleEntryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating VehicleEntry with WAITING status.
    Used when customer submits pre-order via Telegram bot.
    """

    class Meta:
        model = VehicleEntry
        fields = (
            "license_plate",
            "customer",
            "vehicle_type",
        )

    def create(self, validated_data):
        """Create vehicle entry with WAITING status."""
        validated_data["status"] = "WAITING"
        validated_data["entry_time"] = None  # Not arrived yet
        return super().create(validated_data)


class VehicleEntryUpdateStatusSerializer(serializers.Serializer):
    """
    Serializer for updating VehicleEntry status.
    """

    status = serializers.ChoiceField(choices=VehicleEntry.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
