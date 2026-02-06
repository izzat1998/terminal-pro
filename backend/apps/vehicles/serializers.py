from rest_framework import serializers

from apps.accounts.models import CustomUser
from apps.files.models import File
from apps.files.serializers import FileSerializer

from .models import Destination, VehicleEntry


class UserInfoSerializer(serializers.Serializer):
    """
    Nested serializer for user info (customer/manager) in VehicleEntry response
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source="first_name", read_only=True)
    phone = serializers.CharField(source="phone_number", read_only=True)
    company_name = serializers.SerializerMethodField()
    company_slug = serializers.SerializerMethodField()

    def get_company_name(self, obj):
        """Get company name from profile or legacy field"""
        if (
            hasattr(obj, "customer_profile")
            and obj.customer_profile
            and obj.customer_profile.company
        ):
            return obj.customer_profile.company.name
        if hasattr(obj, "company") and obj.company:
            return obj.company.name
        return None

    def get_company_slug(self, obj):
        """Get company slug from profile or legacy field"""
        if (
            hasattr(obj, "customer_profile")
            and obj.customer_profile
            and obj.customer_profile.company
        ):
            return obj.customer_profile.company.slug
        if hasattr(obj, "company") and obj.company:
            return obj.company.slug
        return None


class DestinationSerializer(serializers.ModelSerializer):
    """
    Serializer for Destination model with zone
    """

    class Meta:
        model = Destination
        fields = ["id", "name", "code", "zone", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at", "code"]


class VehicleEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for VehicleEntry with conditional field validation
    Supports multiple entry photos via entry_photo_files field
    """

    # Write-only fields for photo uploads (supports multiple files)
    # Required only on create, not on update
    entry_photo_files = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="Список фото автомобиля при въезде (можно несколько)",
    )
    exit_photo_files = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="Список фото автомобиля при выезде (можно несколько)",
    )

    # Read-only nested photo details (returns list)
    entry_photos = FileSerializer(many=True, read_only=True)
    exit_photos = FileSerializer(many=True, read_only=True)

    # Read-only computed fields
    is_on_terminal = serializers.BooleanField(read_only=True)
    dwell_time_hours = serializers.FloatField(read_only=True)

    # Nested user info (manager who recorded)
    manager = UserInfoSerializer(source="recorded_by", read_only=True)

    # Customer ID for write operations
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(user_type="customer"),
        source="customer",
        required=False,
        allow_null=True,
        write_only=True,
        help_text="ID клиента для привязки к записи",
    )

    # Read-only nested customer info for display
    customer = UserInfoSerializer(read_only=True)

    # Nested destination object (full details)
    destination_details = DestinationSerializer(source="destination", read_only=True)

    # Status display
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # Display labels for choice fields (Russian)
    vehicle_type_display = serializers.CharField(
        source="get_vehicle_type_display", read_only=True
    )
    visitor_type_display = serializers.CharField(
        source="get_visitor_type_display", read_only=True
    )
    transport_type_display = serializers.CharField(
        source="get_transport_type_display", read_only=True
    )
    entry_load_status_display = serializers.CharField(
        source="get_entry_load_status_display", read_only=True
    )
    cargo_type_display = serializers.CharField(
        source="get_cargo_type_display", read_only=True
    )
    container_size_display = serializers.CharField(
        source="get_container_size_display", read_only=True
    )
    container_load_status_display = serializers.CharField(
        source="get_container_load_status_display", read_only=True
    )
    exit_load_status_display = serializers.CharField(
        source="get_exit_load_status_display", read_only=True
    )

    class Meta:
        model = VehicleEntry
        fields = [
            "id",
            # Status
            "status",
            "status_display",
            # Entry fields
            "license_plate",
            "entry_photo_files",  # Changed: now accepts multiple files
            "entry_photos",  # Changed: now returns list of photos
            "entry_time",
            # Manager who recorded (nested object, read-only)
            "manager",
            # Customer who created pre-order
            "customer_id",  # Write-only: accepts ID
            "customer",  # Read-only: nested customer info
            # Vehicle type
            "vehicle_type",
            "vehicle_type_display",
            # Light vehicle fields
            "visitor_type",
            "visitor_type_display",
            # Cargo vehicle fields
            "transport_type",
            "transport_type_display",
            "entry_load_status",
            "entry_load_status_display",
            "cargo_type",
            "cargo_type_display",
            "container_size",
            "container_size_display",
            "container_load_status",
            "container_load_status_display",
            # Location
            "destination",
            "destination_details",
            # Exit fields
            "exit_photo_files",
            "exit_photos",
            "exit_time",
            "exit_load_status",
            "exit_load_status_display",
            # Computed
            "is_on_terminal",
            "dwell_time_hours",
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "recorded_by",
            # Note: "status" removed to allow frontend to set status for exit/revert operations
            "created_at",
            "updated_at",
            "is_on_terminal",
            "dwell_time_hours",
        ]

    def validate_license_plate(self, value):
        """Normalize license plate to uppercase"""
        return value.upper().strip()

    def validate(self, attrs):
        """
        Conditional validation based on vehicle type and workflow path

        CREATE: Full validation - all conditional fields required
        UPDATE: Validate only if conditional fields are ACTUALLY CHANGING
        """
        is_create = self.instance is None

        # entry_photo_files are optional for web interface
        # Telegram check-in endpoint handles photos separately with validation
        # Web interface allows creating entries without photos (for backdating, corrections, etc.)

        # Fields that trigger conditional validation when CHANGED (not just present)
        conditional_fields = {"vehicle_type", "entry_load_status", "cargo_type"}

        # On update, skip validation unless a conditional field is ACTUALLY CHANGING
        if not is_create:
            # Check if any conditional field is actually changing (different from instance)
            fields_actually_changing = set()
            for field in conditional_fields:
                if field in attrs:
                    current_value = getattr(self.instance, field, None)
                    new_value = attrs[field]
                    if new_value != current_value:
                        fields_actually_changing.add(field)

            if not fields_actually_changing:
                return (
                    attrs  # Simple update (destination, photos, etc.) - no validation
                )

        # Get vehicle_type (from attrs for create, or merged with instance for update)
        vehicle_type = attrs.get("vehicle_type")
        if not is_create and vehicle_type is None:
            vehicle_type = self.instance.vehicle_type

        # Light vehicle validation
        if vehicle_type == "LIGHT":
            visitor_type = attrs.get("visitor_type")
            if not is_create:
                visitor_type = visitor_type or self.instance.visitor_type
            if not visitor_type:
                raise serializers.ValidationError(
                    {"visitor_type": "Обязательное поле для легкового автомобиля"}
                )

        # Cargo vehicle validation
        elif vehicle_type == "CARGO":
            # Get values (from attrs or instance for update)
            transport_type = attrs.get("transport_type")
            entry_load_status = attrs.get("entry_load_status")
            cargo_type = attrs.get("cargo_type")
            container_size = attrs.get("container_size")
            container_load_status = attrs.get("container_load_status")

            if not is_create:
                transport_type = transport_type or self.instance.transport_type
                entry_load_status = entry_load_status or self.instance.entry_load_status
                cargo_type = cargo_type or self.instance.cargo_type
                container_size = container_size or self.instance.container_size
                container_load_status = (
                    container_load_status or self.instance.container_load_status
                )

            if not transport_type:
                raise serializers.ValidationError(
                    {"transport_type": "Обязательное поле для грузового автомобиля"}
                )

            if not entry_load_status:
                raise serializers.ValidationError(
                    {"entry_load_status": "Обязательное поле для грузового автомобиля"}
                )

            # Loaded cargo validation
            if entry_load_status == "LOADED":
                if not cargo_type:
                    raise serializers.ValidationError(
                        {"cargo_type": "Обязательное поле для груженого автомобиля"}
                    )

                # Container cargo validation
                if cargo_type == "CONTAINER":
                    if not container_size:
                        raise serializers.ValidationError(
                            {
                                "container_size": "Обязательное поле для контейнерного груза"
                            }
                        )
                    if not container_load_status:
                        raise serializers.ValidationError(
                            {
                                "container_load_status": "Обязательное поле для контейнерного груза"
                            }
                        )

        return attrs

    def create(self, validated_data):
        """
        Create vehicle entry with optional photo upload handling
        Auto-sets entry_time for ON_TERMINAL entries (direct creation from frontend/API)
        """
        from django.utils import timezone

        # Extract photo files list (optional for web interface)
        entry_photo_files = validated_data.pop("entry_photo_files", []) or []

        # Note: customer is handled automatically by PrimaryKeyRelatedField

        # Auto-set entry_time for ON_TERMINAL status (direct entry, not pre-order)
        # WAITING entries should have null entry_time until check-in
        status = validated_data.get("status", "ON_TERMINAL")
        if status == "ON_TERMINAL" and not validated_data.get("entry_time"):
            validated_data["entry_time"] = timezone.now()

        # Create the entry first (without photos)
        entry = super().create(validated_data)

        # Upload each photo and add to ManyToMany relationship (if any provided)
        for photo_file in entry_photo_files:
            entry_photo = File.objects.create_from_upload(
                uploaded_file=photo_file,
                category_code="vehicle_photo",
                user=validated_data.get("recorded_by"),
                is_public=False,
            )
            # Add photo to the ManyToMany field
            entry.entry_photos.add(entry_photo)

        return entry

    def update(self, instance, validated_data):
        """
        Update vehicle entry - photos are optional during update
        Clears irrelevant fields when vehicle_type or related fields change
        AUTO-TRANSITIONS status when exit_time is set (safety net)
        """
        # Note: customer is handled automatically by PrimaryKeyRelatedField

        # === AUTO-STATUS TRANSITION (Safety Net) ===
        # If exit_time is being set and vehicle is ON_TERMINAL, auto-set status to EXITED
        # This is a fallback for direct API calls, Django Admin, edit modal, etc.
        # Frontend should use /exit/ endpoint which sends notifications
        # This safety net prevents data inconsistency
        if validated_data.get("exit_time"):
            if instance.status == "ON_TERMINAL" and "status" not in validated_data:
                validated_data["status"] = "EXITED"
                # Note: No notification sent here - use /exit/ endpoint for notifications

        # === FIELD CLEARING LOGIC ===
        # Clear irrelevant fields based on what's changing

        new_vehicle_type = validated_data.get("vehicle_type")
        new_entry_load_status = validated_data.get("entry_load_status")
        new_cargo_type = validated_data.get("cargo_type")

        # 1. vehicle_type changing
        if new_vehicle_type and new_vehicle_type != instance.vehicle_type:
            if new_vehicle_type == "LIGHT":
                # CARGO → LIGHT: Clear all cargo-related fields
                validated_data.setdefault("transport_type", None)
                validated_data.setdefault("entry_load_status", None)
                validated_data.setdefault("cargo_type", None)
                validated_data.setdefault("container_size", None)
                validated_data.setdefault("container_load_status", None)
            elif new_vehicle_type == "CARGO":
                # LIGHT → CARGO: Clear visitor_type
                validated_data.setdefault("visitor_type", None)

        # 2. entry_load_status changing to EMPTY
        if new_entry_load_status == "EMPTY" and instance.entry_load_status == "LOADED":
            # LOADED → EMPTY: Clear cargo fields
            validated_data.setdefault("cargo_type", None)
            validated_data.setdefault("container_size", None)
            validated_data.setdefault("container_load_status", None)

        # 3. cargo_type changing from CONTAINER to something else
        if (
            new_cargo_type
            and new_cargo_type != "CONTAINER"
            and instance.cargo_type == "CONTAINER"
        ):
            # CONTAINER → other: Clear container fields
            validated_data.setdefault("container_size", None)
            validated_data.setdefault("container_load_status", None)

        # 4. cargo_type being cleared (set to None)
        if "cargo_type" in validated_data and validated_data["cargo_type"] is None:
            # Clear container fields when cargo_type is None
            validated_data.setdefault("container_size", None)
            validated_data.setdefault("container_load_status", None)

        # === PHOTO UPLOAD HANDLING ===
        # Handle optional entry photo uploads
        entry_photo_files = validated_data.pop("entry_photo_files", None)
        if entry_photo_files:
            for photo_file in entry_photo_files:
                entry_photo = File.objects.create_from_upload(
                    uploaded_file=photo_file,
                    category_code="vehicle_photo",
                    user=validated_data.get("recorded_by", instance.recorded_by),
                    is_public=False,
                )
                instance.entry_photos.add(entry_photo)

        # Handle optional exit photo uploads
        exit_photo_files = validated_data.pop("exit_photo_files", None)
        if exit_photo_files:
            for photo_file in exit_photo_files:
                exit_photo = File.objects.create_from_upload(
                    uploaded_file=photo_file,
                    category_code="vehicle_photo",
                    user=validated_data.get("recorded_by", instance.recorded_by),
                    is_public=False,
                )
                instance.exit_photos.add(exit_photo)

        # Update remaining fields
        return super().update(instance, validated_data)


class VehicleExitSerializer(serializers.Serializer):
    """
    Simplified serializer for registering vehicle exit
    Supports multiple exit photos
    """

    license_plate = serializers.CharField(
        required=True, help_text="Государственный номер автомобиля"
    )
    exit_photo_files = serializers.ListField(
        child=serializers.ImageField(),
        required=False,  # Optional - web interface may not have photos
        allow_empty=True,
        help_text="Список фото автомобиля при выезде (опционально)",
    )
    exit_time = serializers.DateTimeField(
        required=True,
        input_formats=["iso-8601", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"],
        help_text="Время выезда в ISO формате",
    )
    exit_load_status = serializers.ChoiceField(
        choices=VehicleEntry.LOAD_STATUS_CHOICES,
        required=False,
        help_text="Статус загрузки при выезде (только для грузовых)",
    )

    def validate_license_plate(self, value):
        """Normalize license plate to uppercase"""
        return value.upper().strip()


class PlateRecognitionRequestSerializer(serializers.Serializer):
    """
    Serializer for license plate recognition API request
    """

    image = serializers.ImageField(
        required=True, help_text="Фото номерного знака автомобиля"
    )
    region = serializers.CharField(
        required=False,
        default="uz",
        help_text="Регион распознавания (uz, ru, us, eu, и т.д.)",
    )


class PlateRecognitionResponseSerializer(serializers.Serializer):
    """
    Serializer for license plate recognition API response
    """

    success = serializers.BooleanField()
    plate_number = serializers.CharField(allow_blank=True)
    confidence = serializers.FloatField()
    error_message = serializers.CharField(allow_null=True, required=False)


class VehicleCheckInSerializer(serializers.Serializer):
    """
    Serializer for checking in a WAITING vehicle (transition to ON_TERMINAL)
    Used when manager at gate registers arrival of a pre-ordered vehicle.
    Entry time is set automatically by the backend to current time.
    """

    license_plate = serializers.CharField(
        required=True, help_text="Государственный номер автомобиля"
    )
    entry_photo_files = serializers.ListField(
        child=serializers.ImageField(),
        required=True,
        help_text="Список фото автомобиля при въезде (обязательно)",
    )

    def validate_license_plate(self, value):
        """Normalize license plate to uppercase"""
        return value.upper().strip()
