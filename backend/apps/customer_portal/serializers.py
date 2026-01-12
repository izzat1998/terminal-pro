"""
Serializers for customer portal API endpoints.

These serializers provide customer-facing representations of data,
hiding admin-only fields and enforcing customer-specific business rules.
"""

from rest_framework import serializers

from apps.accounts.models import Company, CustomerProfile, CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, ContainerOwner, PreOrder


# ============ Nested Serializers ============


class CustomerCompanySerializer(serializers.ModelSerializer):
    """
    Simplified company serializer for nested representation in customer portal.
    """

    class Meta:
        model = Company
        fields = ("id", "name", "slug")
        read_only_fields = fields


class ContainerNestedSerializer(serializers.ModelSerializer):
    """
    Nested serializer for container data in customer portal.
    """

    class Meta:
        model = Container
        fields = ("id", "container_number", "iso_type")
        read_only_fields = fields


class ContainerOwnerNestedSerializer(serializers.ModelSerializer):
    """
    Nested serializer for container owner in customer portal.
    """

    class Meta:
        model = ContainerOwner
        fields = ("id", "name")
        read_only_fields = fields


class CustomerFileSerializer(serializers.Serializer):
    """
    Simplified file serializer for customer portal.
    Returns only essential fields for displaying images.
    """

    id = serializers.UUIDField()
    file_url = serializers.SerializerMethodField()
    original_filename = serializers.CharField()
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)

    def get_file_url(self, obj):
        """Get full URL for the file."""
        request = self.context.get("request")
        if obj.file and hasattr(obj.file, "url"):
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class VehicleEntrySerializer(serializers.Serializer):
    """
    Simplified vehicle entry serializer for nested representation in pre-orders.
    """

    id = serializers.IntegerField()
    status = serializers.CharField()
    license_plate = serializers.CharField()


# ============ Customer Profile Serializers ============


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for customer profile.
    Returns customer info with nested company data.
    """

    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "company",
            "is_active",
            "created_at",
        )
        read_only_fields = fields

    def _get_profile(self, obj):
        """Get customer profile, using cached version if available."""
        if not hasattr(obj, "_cached_profile"):
            try:
                obj._cached_profile = obj.customer_profile
            except CustomerProfile.DoesNotExist:
                obj._cached_profile = None
        return obj._cached_profile

    def get_full_name(self, obj):
        """Get customer's full name."""
        return obj.full_name

    def get_phone_number(self, obj):
        """Get phone number from profile first, then legacy field."""
        profile = self._get_profile(obj)
        if profile and profile.phone_number:
            return profile.phone_number
        return obj.phone_number or ""

    def get_company(self, obj):
        """Get company data (id, name, slug)."""
        profile = self._get_profile(obj)
        company = None

        if profile and profile.company:
            company = profile.company
        elif hasattr(obj, "company") and obj.company:
            company = obj.company

        if company:
            return CustomerCompanySerializer(company).data
        return None


class CustomerProfileUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating customer profile.
    Allows updating: first_name, last_name, password.
    """

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    password = serializers.CharField(write_only=True, min_length=8, required=False, style={"input_type": "password"})

    def validate_password(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise serializers.ValidationError("Пароль должен содержать минимум 8 символов")
        return value

    def update(self, instance, validated_data):
        """Update customer profile fields."""
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)

        # Update password if provided
        if "password" in validated_data:
            instance.set_password(validated_data["password"])

        instance.save()
        return instance


# ============ Container Entry Serializers ============


class CustomerContainerEntrySerializer(serializers.ModelSerializer):
    """
    Read-only serializer for container entries (customer view).
    Shows company's containers with essential information.
    Uses nested serializers for foreign key relationships.
    Includes images attached to the container entry.
    """

    container = ContainerNestedSerializer(read_only=True)
    container_owner = ContainerOwnerNestedSerializer(read_only=True)
    company = CustomerCompanySerializer(read_only=True)
    dwell_time_days = serializers.IntegerField(read_only=True)
    images = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = ContainerEntry
        fields = (
            "id",
            "container",
            "status",
            "entry_time",
            "exit_date",
            "dwell_time_days",
            "transport_type",
            "transport_number",
            "exit_transport_type",
            "exit_transport_number",
            "client_name",
            "cargo_name",
            "cargo_weight",
            "location",
            "container_owner",
            "company",
            "images",
            "image_count",
        )
        read_only_fields = fields

    def _get_attachments(self, obj):
        """Cache attachments to avoid multiple queries."""
        if not hasattr(obj, "_cached_attachments"):
            from django.contrib.contenttypes.models import ContentType

            from apps.files.models import FileAttachment

            content_type = ContentType.objects.get_for_model(obj)
            obj._cached_attachments = list(
                FileAttachment.objects.filter(
                    content_type=content_type,
                    object_id=obj.id,
                    file__is_active=True,
                )
                .select_related("file")
                .order_by("display_order", "created_at")
            )
        return obj._cached_attachments

    def get_images(self, obj):
        """Get all image attachments for this container entry."""
        attachments = self._get_attachments(obj)
        images = []
        for attachment in attachments:
            file_obj = attachment.file
            # Only include image files
            if file_obj.mime_type and file_obj.mime_type.startswith("image/"):
                request = self.context.get("request")
                file_url = None
                if file_obj.file and hasattr(file_obj.file, "url"):
                    if request:
                        file_url = request.build_absolute_uri(file_obj.file.url)
                    else:
                        file_url = file_obj.file.url
                images.append(
                    {
                        "id": str(file_obj.id),
                        "file_url": file_url,
                        "original_filename": file_obj.original_filename,
                        "width": file_obj.width,
                        "height": file_obj.height,
                    }
                )
        return images

    def get_image_count(self, obj):
        """Get count of image attachments."""
        attachments = self._get_attachments(obj)
        return sum(1 for a in attachments if a.file.mime_type and a.file.mime_type.startswith("image/"))


# ============ Pre-Order Serializers ============


class CustomerPreOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for pre-order list/detail (read/write).
    Customer field is hidden (auto-set from request.user).
    """

    vehicle_entry = VehicleEntrySerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PreOrder
        fields = (
            "id",
            "plate_number",
            "operation_type",
            "status",
            "status_display",
            "truck_photo",
            "notes",
            "vehicle_entry",
            "created_at",
            "matched_at",
            "cancelled_at",
            "batch_id",
        )
        read_only_fields = (
            "id",
            "status",
            "status_display",
            "vehicle_entry",
            "created_at",
            "matched_at",
            "cancelled_at",
            "batch_id",
        )


class CustomerPreOrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating pre-orders (customer portal).
    Validates input and prepares data for PreOrderService.
    """

    plate_number = serializers.CharField(max_length=20)
    operation_type = serializers.ChoiceField(choices=PreOrder.OPERATION_CHOICES)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_plate_number(self, value):
        """Normalize and validate plate number."""
        # Remove spaces, dashes, and convert to uppercase
        normalized = value.replace(" ", "").replace("-", "").upper()
        if len(normalized) < 3:
            raise serializers.ValidationError("Номер пластины слишком короткий")
        return normalized

    def validate_operation_type(self, value):
        """Validate operation type is valid."""
        valid_types = [choice[0] for choice in PreOrder.OPERATION_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Недопустимый тип операции. Допустимые значения: {valid_types}")
        return value
