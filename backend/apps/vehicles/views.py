from django.db.models import Case, IntegerField, Value, When
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.files.models import File

from .filters import VehicleEntryFilter
from .models import Destination, VehicleEntry
from .serializers import (
    DestinationSerializer,
    PlateRecognitionRequestSerializer,
    VehicleCheckInSerializer,
    VehicleEntrySerializer,
    VehicleExitSerializer,
)
from .services import VehicleEntryService, VehicleStatisticsService


class DestinationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing destinations

    list: Get all active destinations
    create: Create a new destination (admin only)
    retrieve: Get a specific destination
    update: Update a destination (admin only)
    destroy: Deactivate a destination (soft delete)
    """

    queryset = Destination.objects.filter(is_active=True).order_by("name")
    serializer_class = DestinationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]

    def perform_destroy(self, instance):
        """Soft delete - set is_active=False instead of deleting"""
        instance.is_active = False
        instance.save()


class VehicleEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for vehicle entries (gate checkpoint journal).

    WORKFLOW ENDPOINTS (Recommended - use these for state transitions):
    - POST /entries/                  → Create new entry
    - POST /entries/check-in/         → WAITING → ON_TERMINAL (with notifications)
    - POST /entries/exit/             → ON_TERMINAL → EXITED (with notifications)
    - POST /entries/{id}/cancel/      → WAITING → CANCELLED (with notifications)
    - GET  /entries/on-terminal/      → List vehicles currently on terminal

    ADMINISTRATIVE ENDPOINTS (Use for corrections and data updates):
    - GET    /entries/                → List all entries with filtering
    - GET    /entries/{id}/           → Retrieve specific entry
    - PUT    /entries/{id}/           → Update entry fields (no notifications)
    - PATCH  /entries/{id}/           → Partial update (no notifications)
    - DELETE /entries/{id}/           → Delete entry

    IMPORTANT: Use workflow endpoints for state transitions to ensure:
    - Automatic status updates via service layer
    - Telegram notifications to customers
    - Validation of business rules (exit_time > entry_time, etc.)
    - Proper audit logging

    Use administrative PUT/PATCH only for:
    - Correcting vehicle details (license plate, type, load status)
    - Administrative corrections (revert exit, fix data, backdating)
    - Direct edits via Django Admin

    Note: Serializer has auto-status safety net - setting exit_time via PUT
    will auto-change status to EXITED if vehicle is ON_TERMINAL. However,
    this does NOT send notifications. Use /exit/ endpoint for full workflow.
    """

    queryset = VehicleEntry.objects.all()
    serializer_class = VehicleEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VehicleEntryFilter
    search_fields = [
        "license_plate",
        "customer__first_name",
        "customer__phone_number",
        "recorded_by__username",
        "recorded_by__first_name",
        "destination__name",
    ]
    ordering_fields = [
        "entry_time",
        "exit_time",
        "license_plate",
        "status",
        "created_at",
    ]
    # Note: Default ordering is applied in get_queryset, not here

    def get_queryset(self):
        """Optimize query with select_related and prefetch_related.
        Orders by status (WAITING -> ON_TERMINAL -> EXITED -> CANCELLED), then by entry_time descending.
        """
        # Custom ordering: WAITING=0, ON_TERMINAL=1, EXITED=2, CANCELLED=3
        status_order = Case(
            When(status="WAITING", then=Value(0)),
            When(status="ON_TERMINAL", then=Value(1)),
            When(status="EXITED", then=Value(2)),
            When(status="CANCELLED", then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )

        return (
            VehicleEntry.objects.select_related(
                "recorded_by",
                "destination",
                "customer",
                "customer__customer_profile",
                "customer__customer_profile__company",
                "customer__company",  # Legacy field
            )
            .prefetch_related("entry_photos", "exit_photos")
            .annotate(status_order=status_order)
            .order_by("status_order", "-created_at")
        )

    def filter_queryset(self, queryset):
        """Apply filters but preserve our custom ordering if no ordering param specified."""
        # Check if user specified ordering in query params
        ordering_param = self.request.query_params.get("ordering")

        # Apply all filter backends
        for backend in list(self.filter_backends):
            # Skip OrderingFilter if no ordering param - we use our default
            if backend == OrderingFilter and not ordering_param:
                continue
            queryset = backend().filter_queryset(self.request, queryset, self)

        return queryset

    def perform_create(self, serializer):
        """Create vehicle entry - serializer handles photo uploads."""
        serializer.save(recorded_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="on-terminal")
    def on_terminal(self, request):
        """
        Get all vehicles currently on terminal (no exit time)

        GET /api/vehicles/entries/on-terminal/
        """
        entry_service = VehicleEntryService()
        vehicles = entry_service.get_vehicles_on_terminal()

        serializer = self.get_serializer(vehicles, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["post"], url_path="exit")
    def exit_vehicle(self, request):
        """
        Register exit for a vehicle by license plate

        POST /api/vehicles/entries/exit/

        Request body (multipart/form-data):
        {
            "license_plate": "01A123BC",
            "exit_photo_files": [<file>, <file>, ...],
            "exit_time": "2025-11-20T14:30:00Z",
            "exit_load_status": "EMPTY"  // optional, for cargo vehicles
        }
        """
        # Validate request
        exit_serializer = VehicleExitSerializer(data=request.data)
        if not exit_serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Ошибка валидации",
                        "details": exit_serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = exit_serializer.validated_data
        license_plate = validated_data["license_plate"]

        # Upload exit photos (optional)
        exit_photo_files = validated_data.get("exit_photo_files", [])
        exit_photos = []
        if exit_photo_files:
            for photo_file in exit_photo_files:
                exit_photo = File.objects.create_from_upload(
                    uploaded_file=photo_file,
                    category_code="vehicle_photo",
                    user=request.user,
                    is_public=False,
                )
                exit_photos.append(exit_photo)

        # Register exit via service layer
        entry_service = VehicleEntryService()
        entry = entry_service.register_exit(
            license_plate=license_plate,
            exit_photos=exit_photos,
            exit_time=validated_data["exit_time"],
            exit_load_status=validated_data.get("exit_load_status"),
        )

        # Return updated entry
        response_serializer = VehicleEntrySerializer(entry)
        return Response({"success": True, "data": response_serializer.data})

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        """
        Check in a WAITING vehicle - transition to ON_TERMINAL status

        Used when manager at the gate registers arrival of a pre-ordered vehicle.
        Finds vehicle by license plate and updates status from WAITING to ON_TERMINAL.
        Entry time is automatically set to current time by the backend.

        POST /api/vehicles/entries/check-in/

        Request body (multipart/form-data):
        {
            "license_plate": "01A123BC",
            "entry_photo_files": [<file>, <file>, ...]
        }

        Response:
        - 200: Vehicle checked in successfully (returns VehicleEntry)
        - 400: Validation error
        - 404: Waiting vehicle not found
        """
        # Validate request
        check_in_serializer = VehicleCheckInSerializer(data=request.data)
        if not check_in_serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Ошибка валидации",
                        "details": check_in_serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = check_in_serializer.validated_data
        license_plate = validated_data["license_plate"]

        # Upload entry photos
        entry_photo_files = validated_data["entry_photo_files"]
        entry_photos = []
        for photo_file in entry_photo_files:
            entry_photo = File.objects.create_from_upload(
                uploaded_file=photo_file,
                category_code="vehicle_photo",
                user=request.user,
                is_public=False,
            )
            entry_photos.append(entry_photo)

        # Check in via service layer (entry_time set automatically)
        entry_service = VehicleEntryService()
        entry = entry_service.check_in(
            license_plate=license_plate,
            entry_photos=entry_photos,
            recorded_by=request.user,
        )

        # Return updated entry
        response_serializer = VehicleEntrySerializer(entry)
        return Response({"success": True, "data": response_serializer.data})

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_entry(self, request, pk=None):
        """
        Cancel a WAITING vehicle entry (WAITING → CANCELLED)

        POST /api/vehicles/entries/{id}/cancel/

        Response:
        - 200: Entry cancelled successfully (returns VehicleEntry)
        - 400: Entry not in WAITING status
        - 404: Entry not found
        """
        entry_service = VehicleEntryService()
        entry = entry_service.cancel_by_id(entry_id=pk)

        response_serializer = VehicleEntrySerializer(entry)
        return Response({"success": True, "data": response_serializer.data})


class PlateRecognizerAPIView(APIView):
    """
    License Plate Recognition API (authenticated access).
    Uses shared PlateRecognizerAPIService for plate recognition.
    """

    permission_classes = [IsAuthenticated]

    @property
    def plate_service(self):
        from apps.core.services.plate_recognizer_service import (
            PlateRecognizerAPIService,
        )

        return PlateRecognizerAPIService()

    def post(self, request):
        """Recognize license plate from uploaded image."""
        request_serializer = PlateRecognitionRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error_message": "Invalid request",
                    "details": request_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = request_serializer.validated_data
        image_bytes = validated_data["image"].read()
        region = validated_data.get("region", "uz")

        result = self.plate_service.recognize_plate(image_bytes, region)

        return Response(
            {
                "success": result.success,
                "plate_number": result.plate_number,
                "confidence": result.confidence,
                "error_message": result.error_message,
            },
            status=status.HTTP_200_OK
            if result.success
            else status.HTTP_400_BAD_REQUEST,
        )


class VehicleChoicesAPIView(APIView):
    """
    Returns all choice options for vehicle entry forms

    GET /api/vehicles/choices/

    Response:
    {
        "vehicle_types": [{"value": "LIGHT", "label": "Легковой автомобиль"}, ...],
        "visitor_types": [...],
        "transport_types": [...],
        "load_statuses": [...],
        "cargo_types": [...],
        "container_sizes": [...]
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        def choices_to_list(choices):
            return [{"value": value, "label": label} for value, label in choices]

        return Response(
            {
                "success": True,
                "data": {
                    "vehicle_types": choices_to_list(VehicleEntry.VEHICLE_TYPE_CHOICES),
                    "visitor_types": choices_to_list(VehicleEntry.VISITOR_TYPE_CHOICES),
                    "transport_types": choices_to_list(
                        VehicleEntry.TRANSPORT_TYPE_CHOICES
                    ),
                    "load_statuses": choices_to_list(VehicleEntry.LOAD_STATUS_CHOICES),
                    "cargo_types": choices_to_list(VehicleEntry.CARGO_TYPE_CHOICES),
                    "container_sizes": choices_to_list(
                        VehicleEntry.CONTAINER_SIZE_CHOICES
                    ),
                },
            }
        )


class VehicleStatisticsAPIView(APIView):
    """
    Vehicle terminal statistics for dashboard

    GET /api/vehicles/statistics/
    GET /api/vehicles/statistics/?overstayer_hours=24

    Response includes:
    - current: Vehicles on terminal with breakdowns
    - time_metrics: Average dwell time, longest stay
    - overstayers: Vehicles exceeding threshold
    - last_30_days: Historical entry/exit data
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get configurable overstayer threshold (default: 24 hours)
        overstayer_hours = int(request.query_params.get("overstayer_hours", 24))

        stats_service = VehicleStatisticsService()
        statistics = stats_service.get_all_statistics(overstayer_hours)

        return Response({"success": True, "data": statistics})
