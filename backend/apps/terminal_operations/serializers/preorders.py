"""
PreOrder serializers.

Handles customer pre-order CRUD operations with nested relationships.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


class VehicleEntryNestedSerializer(serializers.Serializer):
    """
    Lightweight nested serializer for VehicleEntry in PreOrder responses
    """

    id = serializers.IntegerField()
    license_plate = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.SerializerMethodField()
    entry_time = serializers.DateTimeField()
    exit_time = serializers.DateTimeField()

    def get_status_display(self, obj):
        return obj.get_status_display() if obj else None


class ContainerEntryNestedSerializer(serializers.Serializer):
    """
    Lightweight nested serializer for ContainerEntry (matched_entry) in PreOrder responses
    """

    id = serializers.IntegerField()
    container_number = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    entry_time = serializers.DateTimeField()
    client_name = serializers.CharField()

    def get_container_number(self, obj):
        return obj.container.container_number if obj.container else None

    def get_status(self, obj):
        return obj.get_status_display() if obj else None


class CustomerNestedSerializer(serializers.Serializer):
    """
    Nested serializer for Customer in PreOrder responses
    """

    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField()
    company = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_company(self, obj):
        """Get company info from profile or legacy field"""
        company = None
        if (
            hasattr(obj, "customer_profile")
            and obj.customer_profile
            and obj.customer_profile.company
        ):
            company = obj.customer_profile.company
        elif hasattr(obj, "company") and obj.company:
            company = obj.company

        if company:
            return {"id": company.id, "name": company.name, "slug": company.slug}
        return None


class PreOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for PreOrder model.
    Returns nested objects for all FK relationships.
    """

    operation_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    truck_photo_url = serializers.SerializerMethodField()

    class Meta:
        from ..models import PreOrder

        model = PreOrder
        fields = (
            "id",
            "customer",
            "plate_number",
            "operation_type",
            "operation_type_display",
            "status",
            "status_display",
            "truck_photo",
            "truck_photo_url",
            "vehicle_entry",
            "matched_entry",
            "matched_at",
            "cancelled_at",
            "notes",
            "batch_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "vehicle_entry",
            "matched_entry",
            "matched_at",
            "cancelled_at",
            "batch_id",
            "created_at",
            "updated_at",
        )

    def to_representation(self, instance):
        """Return nested objects for all FK relationships"""
        data = super().to_representation(instance)

        # Customer - return nested object
        if instance.customer:
            data["customer"] = CustomerNestedSerializer(instance.customer).data
        else:
            data["customer"] = None

        # Vehicle entry - return nested object
        if instance.vehicle_entry:
            data["vehicle_entry"] = VehicleEntryNestedSerializer(
                instance.vehicle_entry
            ).data
        else:
            data["vehicle_entry"] = None

        # Matched entry - return nested object
        if instance.matched_entry:
            data["matched_entry"] = ContainerEntryNestedSerializer(
                instance.matched_entry
            ).data
        else:
            data["matched_entry"] = None

        return data

    @extend_schema_field(OpenApiTypes.STR)
    def get_operation_type_display(self, obj):
        """Get human-readable operation type."""
        return obj.get_operation_type_display()

    @extend_schema_field(OpenApiTypes.STR)
    def get_status_display(self, obj):
        """Get human-readable status."""
        return obj.get_status_display()

    @extend_schema_field({"type": "string", "nullable": True, "format": "uri"})
    def get_truck_photo_url(self, obj):
        """Get URL for truck photo."""
        if obj.truck_photo and obj.truck_photo.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.truck_photo.file.url)
            return obj.truck_photo.file.url
        return None


class PreOrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for PreOrder list views.
    """

    customer_name = serializers.SerializerMethodField()
    operation_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        from ..models import PreOrder

        model = PreOrder
        fields = (
            "id",
            "customer_name",
            "plate_number",
            "operation_type",
            "operation_type_display",
            "status",
            "status_display",
            "created_at",
        )

    @extend_schema_field({"type": "string", "nullable": True})
    def get_customer_name(self, obj):
        return obj.customer.full_name if obj.customer else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_operation_type_display(self, obj):
        return obj.get_operation_type_display()

    @extend_schema_field(OpenApiTypes.STR)
    def get_status_display(self, obj):
        return obj.get_status_display()
