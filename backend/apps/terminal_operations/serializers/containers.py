"""
Container entry serializers.

Handles ContainerEntry CRUD operations, file attachments, and Excel import.
"""

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import Company
from apps.containers.models import Container

from ..models import ContainerEntry, ContainerOwner, CraneOperation
from .base import (
    ContainerNestedSerializer,
    ContainerOwnerSerializer,
    CraneOperationSerializer,
    CraneOperationWriteSerializer,
    UserNestedSerializer,
)


class ContainerEntrySerializer(serializers.ModelSerializer):
    # Write-only fields for container info
    container_number = serializers.CharField(write_only=True, required=True)
    container_iso_type = serializers.CharField(write_only=True, required=True)
    # Override to accept Russian values - remove model choice validation
    status = serializers.CharField(required=True)
    transport_type = serializers.CharField(required=True)
    exit_transport_type = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    # Read-only calculated field
    dwell_time_days = serializers.SerializerMethodField()
    # Accept company ID for write operations
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True),
        source="company",
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Company ID (optional, auto-populates client_name)",
    )
    # Make entry_time writable for historical entries (admin can override)
    # Don't use allow_null=True so Django's default=timezone.now works when not provided
    entry_time = serializers.DateTimeField(required=False)
    # Explicitly define datetime fields for proper parsing
    exit_date = serializers.DateTimeField(required=False, allow_null=True)
    additional_crane_operation_date = serializers.DateTimeField(
        required=False, allow_null=True
    )
    # Nested crane operations (read-only for responses)
    crane_operations = CraneOperationSerializer(many=True, read_only=True)
    # Write-only: accept array of crane operations when creating/updating entry
    crane_operations_data = CraneOperationWriteSerializer(
        many=True, write_only=True, required=False
    )
    # Explicitly define ForeignKey field to allow null
    container_owner = serializers.PrimaryKeyRelatedField(
        queryset=ContainerOwner.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ContainerEntry
        fields = [
            "id",
            "container",
            "container_number",
            "container_iso_type",
            "status",
            "transport_type",
            "transport_number",
            "entry_train_number",
            "entry_time",
            "recorded_by",
            "client_name",
            "company",
            "company_id",
            "container_owner",
            "cargo_name",
            "exit_date",
            "exit_transport_type",
            "exit_train_number",
            "exit_transport_number",
            "destination_station",
            "location",
            "additional_crane_operation_date",
            "crane_operations",
            "crane_operations_data",
            "note",
            "dwell_time_days",
            "cargo_weight",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "container",
            "created_at",
            "updated_at",
            "dwell_time_days",
            "crane_operations",
            "company",
        ]

    @extend_schema_field({"type": "integer", "nullable": True})
    def get_dwell_time_days(self, obj):
        """Return calculated dwell time in days"""
        return obj.dwell_time_days

    def to_representation(self, instance):
        """Return Russian display values for choice fields and full nested objects for FKs"""
        data = super().to_representation(instance)

        # Container - return full nested object
        data["container"] = ContainerNestedSerializer(instance.container).data

        # Choice fields - return Russian display values
        data["status"] = instance.get_status_display()
        data["transport_type"] = instance.get_transport_type_display()
        if instance.exit_transport_type:
            data["exit_transport_type"] = instance.get_exit_transport_type_display()

        # ContainerOwner - return full nested object
        if instance.container_owner:
            data["container_owner"] = ContainerOwnerSerializer(
                instance.container_owner
            ).data
        else:
            data["container_owner"] = None

        # Recorded by - return full nested object
        if instance.recorded_by:
            data["recorded_by"] = UserNestedSerializer(instance.recorded_by).data
        else:
            data["recorded_by"] = None

        # Company - return nested object
        if instance.company:
            data["company"] = {
                "id": instance.company.id,
                "name": instance.company.name,
                "slug": instance.company.slug,
                "is_active": instance.company.is_active,
            }
        else:
            data["company"] = None

        return data

    def validate_container_number(self, value):
        """Validate and normalize container number"""
        return value.upper()

    def validate_container_iso_type(self, value):
        """Validate ISO type against allowed choices"""
        if not value:
            return value

        value = value.upper()
        valid_types = [choice[0] for choice in Container.ISO_TYPE_CHOICES]

        if value not in valid_types:
            valid_types_str = ", ".join(valid_types)
            raise serializers.ValidationError(
                f"Недопустимый тип ISO. Допустимые значения: {valid_types_str}"
            )

        return value

    def _validate_choice_field(self, value, choices, allow_empty=False):
        """
        Validate choice field accepting both DB values and Russian display names.

        Args:
            value: The input value to validate
            choices: The model's CHOICES tuple (e.g., ContainerEntry.STATUS_CHOICES)
            allow_empty: If True, allow None/empty string values

        Returns:
            The database value (converted from Russian if needed)

        Raises:
            ValidationError: If value is not valid
        """
        if allow_empty and not value:
            return value

        russian_to_db = {display: db_value for db_value, display in choices}
        db_value = russian_to_db.get(value, value)

        valid_values = [choice[0] for choice in choices]
        if db_value not in valid_values:
            valid_display = ", ".join([choice[1] for choice in choices])
            raise serializers.ValidationError(
                f"Недопустимое значение. Допустимые значения: {valid_display}"
            )
        return db_value

    def validate_status(self, value):
        """Accept both database values and Russian display names for status"""
        return self._validate_choice_field(value, ContainerEntry.STATUS_CHOICES)

    def validate_transport_type(self, value):
        """Accept both database values and Russian display names for transport type"""
        return self._validate_choice_field(value, ContainerEntry.TRANSPORT_CHOICES)

    def validate_exit_transport_type(self, value):
        """Accept both database values and Russian display names for exit transport type"""
        return self._validate_choice_field(
            value, ContainerEntry.EXIT_TRANSPORT_CHOICES, allow_empty=True
        )

    def validate_recorded_by(self, value):
        """Only admins can override recorded_by field"""
        if value:
            request = self.context.get("request")
            if request and not request.user.is_staff:
                raise serializers.ValidationError(
                    "Тільки адміністратори можуть встановлювати поле recorded_by. Only admins can set recorded_by field."
                )
        return value

    def to_internal_value(self, data):
        """Convert empty strings to None for optional datetime and ForeignKey fields"""
        if isinstance(data, dict):
            # Convert empty strings to None for optional datetime fields
            if data.get("exit_date") == "":
                data["exit_date"] = None
            if data.get("additional_crane_operation_date") == "":
                data["additional_crane_operation_date"] = None
            if data.get("entry_time") == "":
                data.pop("entry_time", None)  # Remove so Django uses default
            # Convert empty string to None for ForeignKey fields
            if data.get("container_owner") == "":
                data["container_owner"] = None
            if data.get("company_id") == "":
                data["company_id"] = None
        return super().to_internal_value(data)

    def validate(self, attrs):
        """Validate container_iso_type is provided when container_number is provided"""
        container_number = attrs.get("container_number")
        container_iso_type = attrs.get("container_iso_type")

        # For updates, if only one is provided, get the other from existing container
        if self.instance and container_number and not container_iso_type:
            # Use existing iso_type if not provided
            attrs["container_iso_type"] = self.instance.container.iso_type
        elif self.instance and container_iso_type and not container_number:
            # Use existing container_number if not provided
            attrs["container_number"] = self.instance.container.container_number
        elif not self.instance and container_number and not container_iso_type:
            # For creates, iso_type is required
            raise serializers.ValidationError(
                {"container_iso_type": "Это поле обязательно при создании записи"}
            )

        # Validate exit_date >= entry_time
        exit_date = attrs.get("exit_date")
        if exit_date and self.instance:
            if exit_date < self.instance.entry_time:
                raise serializers.ValidationError(
                    {"exit_date": "Дата вывоза не может быть раньше даты ввоза"}
                )

        # Auto-populate client_name from company if company provided
        company = attrs.get("company")
        if company and not attrs.get("client_name"):
            attrs["client_name"] = company.name

        return attrs

    def create(self, validated_data):
        """Create entry and associated crane operations"""
        # Extract crane_operations_data before creating entry
        crane_operations_data = validated_data.pop("crane_operations_data", [])

        # Create the entry using parent's create (or manual create)
        entry = ContainerEntry.objects.create(**validated_data)

        # Create associated crane operations
        for op_data in crane_operations_data:
            CraneOperation.objects.create(
                container_entry=entry, operation_date=op_data["operation_date"]
            )

        return entry

    def update(self, instance, validated_data):
        """Update entry and crane operations"""
        # Extract crane_operations_data before updating entry
        crane_operations_data = validated_data.pop("crane_operations_data", None)

        # Update the entry fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If crane_operations_data provided, replace all operations
        if crane_operations_data is not None:
            instance.crane_operations.all().delete()  # Delete existing operations
            for op_data in crane_operations_data:
                CraneOperation.objects.create(
                    container_entry=instance, operation_date=op_data["operation_date"]
                )

        return instance


class ContainerEntryWithImagesSerializer(ContainerEntrySerializer):
    files = serializers.SerializerMethodField()
    file_count = serializers.SerializerMethodField()
    main_file = serializers.SerializerMethodField()

    class Meta(ContainerEntrySerializer.Meta):
        fields = ContainerEntrySerializer.Meta.fields + [
            "files",
            "file_count",
            "main_file",
        ]

    def _get_attachments(self, obj):
        """Cache attachments to avoid multiple queries"""
        if not hasattr(obj, "_cached_attachments"):
            from apps.files.models import FileAttachment

            content_type = ContentType.objects.get_for_model(obj)
            obj._cached_attachments = list(
                FileAttachment.objects.filter(
                    content_type=content_type, object_id=obj.id, file__is_active=True
                )
                .select_related("file")
                .order_by("display_order", "created_at")
            )
        return obj._cached_attachments

    @extend_schema_field({"type": "array", "items": {"type": "object"}})
    def get_files(self, obj):
        """Get all file attachments from new file system"""
        from apps.files.serializers import FileSerializer

        attachments = self._get_attachments(obj)
        data = []
        for attachment in attachments:
            file_serializer = FileSerializer(attachment.file, context=self.context)
            data.append(
                {
                    "attachment_id": attachment.id,
                    "attachment_type": attachment.attachment_type,
                    "description": attachment.description,
                    "display_order": attachment.display_order,
                    "file": file_serializer.data,
                }
            )
        return data

    @extend_schema_field(OpenApiTypes.INT)
    def get_file_count(self, obj):
        """Get count of file attachments from new file system"""
        return len(self._get_attachments(obj))

    @extend_schema_field({"type": "object", "nullable": True})
    def get_main_file(self, obj):
        """Get first file from new file system"""
        from apps.files.serializers import FileSerializer

        attachments = self._get_attachments(obj)
        if attachments:
            attachment = attachments[0]
            file_serializer = FileSerializer(attachment.file, context=self.context)
            return {
                "attachment_id": attachment.id,
                "attachment_type": attachment.attachment_type,
                "description": attachment.description,
                "file": file_serializer.data,
            }
        return None


class ContainerEntryImportSerializer(serializers.Serializer):
    """
    Serializer for Excel file upload and import.
    """

    file = serializers.FileField(
        required=True, help_text="Excel file (.xlsx) with container entries"
    )

    def validate_file(self, value):
        """
        Validate that uploaded file is a valid Excel file.
        """
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds 10MB limit. Current size: {value.size / 1024 / 1024:.2f}MB"
            )

        # Check file extension
        filename = value.name.lower()
        if not filename.endswith(".xlsx"):
            raise serializers.ValidationError(
                "Only .xlsx files are supported. Please use Excel 2007+ format."
            )

        return value


class PlateRecognitionRequestSerializer(serializers.Serializer):
    """
    Serializer for plate recognition request.
    """

    image = serializers.ImageField(
        required=True, help_text="Image file containing license plate (JPEG, PNG, etc.)"
    )
    region = serializers.CharField(
        required=False,
        default="uz",
        max_length=10,
        help_text="Region code for recognition (e.g., uz, ru, us). Default: uz",
    )

    def validate_image(self, value):
        """
        Validate that uploaded file is a valid image.
        """
        # Check file size (max 5MB for plate images)
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image size exceeds 5MB limit. Current size: {value.size / 1024 / 1024:.2f}MB"
            )

        # Check file extension
        allowed_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif"]
        filename = value.name.lower()
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )

        return value


class PlateRecognitionResponseSerializer(serializers.Serializer):
    """
    Serializer for plate recognition response.
    """

    success = serializers.BooleanField(
        help_text="Whether plate recognition was successful"
    )
    plate_number = serializers.CharField(
        required=False, allow_blank=True, help_text="Detected plate number (uppercase)"
    )
    confidence = serializers.FloatField(
        required=False, help_text="Confidence score (0.0 - 1.0)"
    )
    region_code = serializers.CharField(
        required=False, allow_null=True, help_text="Detected region code"
    )
    processing_time = serializers.FloatField(
        required=False, allow_null=True, help_text="API processing time in seconds"
    )
    error_message = serializers.CharField(
        required=False, allow_null=True, help_text="Error message if recognition failed"
    )


class VehicleDetectionResponseSerializer(serializers.Serializer):
    """
    Serializer for enhanced vehicle detection response.

    Includes both plate recognition and vehicle type classification data.
    Used by gate camera integration.
    """

    success = serializers.BooleanField(
        help_text="Whether detection was successful"
    )
    plate_number = serializers.CharField(
        required=False, allow_blank=True, help_text="Detected plate number (uppercase)"
    )
    plate_confidence = serializers.FloatField(
        required=False, help_text="Plate recognition confidence score (0.0 - 1.0)"
    )
    vehicle_type = serializers.CharField(
        required=False,
        help_text="Detected vehicle type: TRUCK, CAR, WAGON, or UNKNOWN"
    )
    vehicle_type_confidence = serializers.FloatField(
        required=False, help_text="Vehicle type confidence score (0.0 - 1.0)"
    )
    vehicle_make = serializers.CharField(
        required=False, allow_null=True, help_text="Detected vehicle make (e.g., Toyota)"
    )
    vehicle_model = serializers.CharField(
        required=False, allow_null=True, help_text="Detected vehicle model (e.g., Camry)"
    )
    vehicle_color = serializers.CharField(
        required=False, allow_null=True, help_text="Detected vehicle color"
    )
    error_message = serializers.CharField(
        required=False, allow_null=True, help_text="Error message if detection failed"
    )
