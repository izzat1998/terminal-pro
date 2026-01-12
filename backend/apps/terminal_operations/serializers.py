import mimetypes

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import Company
from apps.containers.models import Container
from apps.vehicles.models import VehicleEntry

from .models import ContainerEntry, ContainerOwner, CraneOperation


class ContainerOwnerSerializer(serializers.ModelSerializer):
    """
    Serializer for ContainerOwner model
    """

    class Meta:
        model = ContainerOwner
        fields = ["id", "name", "slug", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "slug": {"required": False}  # Auto-generated if not provided
        }

    def validate_name(self, value):
        """Validate name uniqueness on update"""
        if (
            self.instance
            and ContainerOwner.objects.filter(name=value)
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise serializers.ValidationError(
                "Владелец контейнера с таким именем уже существует"
            )
        return value

    def validate_slug(self, value):
        """Validate slug uniqueness on update"""
        if (
            value
            and self.instance
            and ContainerOwner.objects.filter(slug=value)
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise serializers.ValidationError(
                "Владелец контейнера с таким slug уже существует"
            )
        return value


class ContainerNestedSerializer(serializers.ModelSerializer):
    """
    Nested serializer for Container model (read-only, for FK representation)
    """

    class Meta:
        model = Container
        fields = ["id", "container_number", "iso_type"]
        read_only_fields = fields


class UserNestedSerializer(serializers.Serializer):
    """
    Nested serializer for User (recorded_by) - read-only representation
    """
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class CraneOperationSerializer(serializers.ModelSerializer):
    """
    Serializer for CraneOperation model (read-only)
    """

    class Meta:
        model = CraneOperation
        fields = ["id", "operation_date", "created_at"]
        read_only_fields = ["id", "created_at"]


class CraneOperationWriteSerializer(serializers.Serializer):
    """
    Serializer for writing crane operations (used when creating/updating entries)
    Accepts just operation_date without container_entry_id
    """

    operation_date = serializers.DateTimeField()


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
        source='company',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Company ID (optional, auto-populates client_name)"
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
                "is_active": instance.company.is_active
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

    def validate_status(self, value):
        """Accept both database values and Russian display names for status"""
        # Mapping: Russian name -> database value
        russian_to_db = {
            display: db_value for db_value, display in ContainerEntry.STATUS_CHOICES
        }
        db_value = russian_to_db.get(value, value)

        # Validate that the result is a valid database value
        valid_values = [choice[0] for choice in ContainerEntry.STATUS_CHOICES]
        if db_value not in valid_values:
            raise serializers.ValidationError(
                f"Недопустимое значение. Допустимые значения: {', '.join([choice[1] for choice in ContainerEntry.STATUS_CHOICES])}"
            )
        return db_value

    def validate_transport_type(self, value):
        """Accept both database values and Russian display names for transport type"""
        # Mapping: Russian name -> database value
        russian_to_db = {
            display: db_value for db_value, display in ContainerEntry.TRANSPORT_CHOICES
        }
        db_value = russian_to_db.get(value, value)

        # Validate that the result is a valid database value
        valid_values = [choice[0] for choice in ContainerEntry.TRANSPORT_CHOICES]
        if db_value not in valid_values:
            raise serializers.ValidationError(
                f"Недопустимое значение. Допустимые значения: {', '.join([choice[1] for choice in ContainerEntry.TRANSPORT_CHOICES])}"
            )
        return db_value

    def validate_exit_transport_type(self, value):
        """Accept both database values and Russian display names for exit transport type"""
        if not value:  # Allow None or empty string
            return value

        # Mapping: Russian name -> database value
        russian_to_db = {
            display: db_value
            for db_value, display in ContainerEntry.EXIT_TRANSPORT_CHOICES
        }
        db_value = russian_to_db.get(value, value)

        # Validate that the result is a valid database value
        valid_values = [choice[0] for choice in ContainerEntry.EXIT_TRANSPORT_CHOICES]
        if db_value not in valid_values:
            raise serializers.ValidationError(
                f"Недопустимое значение. Допустимые значения: {', '.join([choice[1] for choice in ContainerEntry.EXIT_TRANSPORT_CHOICES])}"
            )
        return db_value

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


class CustomerNamesSerializer(serializers.Serializer):
    """
    Serializer for returning distinct customer names as an array.
    """

    names = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of distinct customer names from container entries",
    )


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

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        valid_mime_types = [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/x-xlsx",
        ]

        if mime_type and mime_type not in valid_mime_types:
            # Warning only - sometimes MIME type detection fails
            pass

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


# ============ PreOrder Serializers ============


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
        if hasattr(obj, "customer_profile") and obj.customer_profile and obj.customer_profile.company:
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
        from .models import PreOrder

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
            data["vehicle_entry"] = VehicleEntryNestedSerializer(instance.vehicle_entry).data
        else:
            data["vehicle_entry"] = None

        # Matched entry - return nested object
        if instance.matched_entry:
            data["matched_entry"] = ContainerEntryNestedSerializer(instance.matched_entry).data
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
        from .models import PreOrder

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


# ============ VehicleEntry Serializers ============


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
