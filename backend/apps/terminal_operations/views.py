import io

from django.db import models
from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.core.exceptions import BusinessLogicError
from apps.core.pagination import StandardResultsSetPagination

from .filters import ContainerEntryFilter
from .models import ContainerEntry, ContainerOwner, CraneOperation
from .serializers import (
    ContainerEntryImportSerializer,
    ContainerEntrySerializer,
    ContainerEntryWithImagesSerializer,
    ContainerOwnerSerializer,
    ContainerPositionSerializer,
    CraneOperationSerializer,
    PlacementAssignRequestSerializer,
    PlacementMoveRequestSerializer,
    PlacementSuggestRequestSerializer,
    PlateRecognitionRequestSerializer,
    PlateRecognitionResponseSerializer,
    PreOrderListSerializer,
    PreOrderSerializer,
)
from .services import (
    ContainerEntryExportService,
    ContainerEntryImportService,
    ContainerEntryService,
    CraneOperationService,
)


class ContainerOwnerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on ContainerOwner model
    """

    queryset = ContainerOwner.objects.all()
    serializer_class = ContainerOwnerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class CraneOperationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on CraneOperation model.
    Allows creating, listing, and deleting crane operations for container entries.
    """

    queryset = CraneOperation.objects.all()
    serializer_class = CraneOperationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["container_entry__container__container_number"]
    ordering_fields = ["operation_date", "created_at"]
    ordering = ["-operation_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crane_service = CraneOperationService()

    def get_queryset(self):
        """
        Filter crane operations by container_entry_id if provided in query params.
        """
        entry_id = self.request.query_params.get("container_entry_id")
        return self.crane_service.get_operations_queryset(
            entry_id=int(entry_id) if entry_id else None
        )

    def perform_create(self, serializer):
        """
        Create crane operation with container_entry from request data or query params.
        Uses CraneOperationService for business logic.
        """
        entry_id = self.request.data.get(
            "container_entry_id"
        ) or self.request.query_params.get("container_entry_id")

        # Service handles validation and entity lookup
        operation = self.crane_service.create_operation(
            entry_id=int(entry_id) if entry_id else None,
            operation_date=serializer.validated_data["operation_date"],
        )

        # Update serializer instance for response
        serializer.instance = operation

    @action(detail=False, methods=["post"], url_path="for-entry")
    def for_entry(self, request):
        """
        Create a crane operation for a specific container entry.
        POST /api/terminal/crane-operations/for-entry/
        Body: {"container_entry_id": 123, "operation_date": "2025-10-28T10:30:00Z"}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry_id = request.data.get("container_entry_id")
        operation = self.crane_service.create_operation(
            entry_id=int(entry_id) if entry_id else None,
            operation_date=serializer.validated_data["operation_date"],
        )

        return Response(
            {"success": True, "data": CraneOperationSerializer(operation).data},
            status=status.HTTP_201_CREATED,
        )


class ContainerEntryViewSet(viewsets.ModelViewSet):
    queryset = ContainerEntry.objects.select_related(
        "container", "recorded_by", "container_owner", "company"
    ).all()
    serializer_class = ContainerEntrySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContainerEntryFilter
    # Allow all standard REST methods including PATCH for partial updates
    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "trace",
    ]
    search_fields = [
        # Container information
        "container__container_number",
        # Transport information
        "transport_number",
        "entry_train_number",
        "exit_train_number",
        "exit_transport_number",
        # Business information
        "client_name",
        "container_owner__name",  # ForeignKey - search by related name
        "cargo_name",
        "destination_station",
        "location",
        # Additional information
        "note",
        # User information
        "recorded_by__username",
        "recorded_by__email",
        "recorded_by__first_name",
        "recorded_by__last_name",
    ]
    ordering_fields = [
        "entry_time",
        "exit_date",
        "status",
        "transport_type",
        "cargo_weight",
        "created_at",
    ]
    ordering = ["-entry_time"]

    @property
    def entry_service(self):
        """
        Get service instance for this request.

        Using @property instead of class attribute ensures:
        - Each request gets a fresh service instance
        - No shared state across concurrent requests
        - Thread-safe operation
        - Follows Django best practices
        """
        return ContainerEntryService()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return ContainerEntryWithImagesSerializer
        return ContainerEntrySerializer

    def perform_create(self, serializer):
        # Get recorded_by override if provided (admin only)
        recorded_by_override = serializer.validated_data.get("recorded_by")

        # Extract crane operations data before creating entry
        crane_operations_data = serializer.validated_data.get(
            "crane_operations_data", []
        )

        entry = self.entry_service.create_entry(
            # Required fields
            container_number=serializer.validated_data["container_number"],
            container_iso_type=serializer.validated_data["container_iso_type"],
            status=serializer.validated_data["status"],
            transport_type=serializer.validated_data["transport_type"],
            user=self.request.user,
            # Optional Stage 1 fields
            transport_number=serializer.validated_data.get("transport_number", ""),
            entry_train_number=serializer.validated_data.get("entry_train_number", ""),
            entry_time=serializer.validated_data.get("entry_time"),
            recorded_by=recorded_by_override,
            # Optional Stage 2 fields (business info)
            client_name=serializer.validated_data.get("client_name", ""),
            company=serializer.validated_data.get("company"),
            container_owner=serializer.validated_data.get("container_owner"),
            cargo_name=serializer.validated_data.get("cargo_name", ""),
            cargo_weight=serializer.validated_data.get("cargo_weight"),
            location=serializer.validated_data.get("location", ""),
            additional_crane_operation_date=serializer.validated_data.get(
                "additional_crane_operation_date"
            ),
            note=serializer.validated_data.get("note", ""),
            # Optional Stage 3 fields (exit info)
            exit_date=serializer.validated_data.get("exit_date"),
            exit_transport_type=serializer.validated_data.get("exit_transport_type"),
            exit_train_number=serializer.validated_data.get("exit_train_number", ""),
            exit_transport_number=serializer.validated_data.get(
                "exit_transport_number", ""
            ),
            destination_station=serializer.validated_data.get(
                "destination_station", ""
            ),
        )

        # Create crane operations if provided
        for op_data in crane_operations_data:
            self.entry_service.add_crane_operation(
                entry_id=entry.id, operation_date=op_data["operation_date"]
            )

        serializer.instance = entry

    def perform_update(self, serializer):
        entry = self.get_object()

        # Extract crane operations data before updating entry
        crane_operations_data = serializer.validated_data.get(
            "crane_operations_data", None
        )

        # Build kwargs with only fields present in validated_data
        # This allows PATCH to work correctly (only update provided fields)
        update_kwargs = {"entry": entry}

        # Map of field names that might be in validated_data
        field_mapping = {
            "container_number": "container_number",
            "container_iso_type": "container_iso_type",
            "status": "status",
            "transport_type": "transport_type",
            "transport_number": "transport_number",
            "entry_train_number": "entry_train_number",
            "client_name": "client_name",
            "company": "company",
            "container_owner": "container_owner",
            "cargo_name": "cargo_name",
            "exit_date": "exit_date",
            "exit_transport_type": "exit_transport_type",
            "exit_train_number": "exit_train_number",
            "exit_transport_number": "exit_transport_number",
            "destination_station": "destination_station",
            "location": "location",
            "additional_crane_operation_date": "additional_crane_operation_date",
            "note": "note",
            "cargo_weight": "cargo_weight",
        }

        # Only include fields that are present in validated_data
        for field_name, kwarg_name in field_mapping.items():
            if field_name in serializer.validated_data:
                update_kwargs[kwarg_name] = serializer.validated_data[field_name]

        updated_entry = self.entry_service.update_entry(**update_kwargs)

        # Replace crane operations if provided
        if crane_operations_data is not None:
            # Delete existing operations first
            updated_entry.crane_operations.all().delete()
            # Then add new ones
            for op_data in crane_operations_data:
                self.entry_service.add_crane_operation(
                    entry_id=updated_entry.id, operation_date=op_data["operation_date"]
                )

        serializer.instance = updated_entry

    @action(detail=False, methods=["get"])
    def recent(self, request):
        """Get recent entries from today"""
        recent_entries = self.entry_service.get_recent_entries()
        page = self.paginate_queryset(recent_entries)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(recent_entries, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get container entry statistics for dashboard.

        GET /api/terminal/entries/stats/

        Returns aggregated statistics:
        - total: Total container entries
        - on_terminal: Containers currently on terminal
        - laden: Laden containers on terminal
        - empty: Empty containers on terminal
        - entered_today: Containers entered today
        - exited_today: Containers exited today
        - companies: Breakdown by company with laden/empty counts
        """
        stats = self.entry_service.get_container_stats()
        return Response({"success": True, "data": stats})

    @action(detail=False, methods=["get"], url_path="executive-dashboard")
    def executive_dashboard(self, request):
        """
        Get comprehensive executive dashboard data.

        GET /api/terminal/entries/executive-dashboard/

        Returns all executive KPIs in a single optimized call:
        - summary: High-level metrics (containers, revenue, vehicles, customers)
        - container_status: Laden/empty breakdown with size distribution
        - revenue_trends: 30-day daily revenue and entry/exit trends
        - top_customers: Top 10 customers by revenue and container count
        - throughput: Entry/exit throughput with 7-day and 30-day totals
        - vehicle_metrics: Vehicles on terminal with dwell time
        - preorder_stats: Pre-order status breakdown

        Query Parameters:
            days: Number of days for historical trends (default: 30)
        """
        from .services import ExecutiveDashboardService

        days = int(request.query_params.get("days", 30))
        dashboard_service = ExecutiveDashboardService()
        data = dashboard_service.get_executive_dashboard(days=days)
        return Response({"success": True, "data": data})

    @action(detail=False, methods=["get"], url_path="by-container")
    def by_container(self, request):
        """Get entries for a specific container"""
        container_number = request.query_params.get("container_number")
        if not container_number:
            raise BusinessLogicError(
                message="container_number parameter required",
                error_code="MISSING_PARAMETER",
            )

        entries = self.entry_service.get_entries_by_container(container_number)
        page = self.paginate_queryset(entries)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(entries, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="check-container")
    def check_container(self, request):
        """
        Check if a container with given number is currently on terminal.

        Used for real-time validation in the create container form.

        GET /api/terminal/entries/check-container/?container_number=MSKU1234567

        Response:
        - 200: { "on_terminal": false }
        - 200: { "on_terminal": true, "entry": { id, container_number, entry_time, status } }
        """
        container_number = (
            request.query_params.get("container_number", "").strip().upper()
        )

        if not container_number or len(container_number) < 4:
            return Response({"on_terminal": False})

        # Check for containers currently on terminal (no exit_date)
        entry = (
            ContainerEntry.objects.filter(
                container__container_number__iexact=container_number,
                exit_date__isnull=True,
            )
            .select_related("container")
            .first()
        )

        if entry:
            return Response(
                {
                    "on_terminal": True,
                    "entry": {
                        "id": entry.id,
                        "container_number": entry.container.container_number,
                        "entry_time": entry.entry_time,
                        "status": entry.status,
                    },
                }
            )

        return Response({"on_terminal": False})

    @action(detail=False, methods=["get"], url_path="customer-names")
    def customer_names(self, request):
        """
        Get distinct customer names from all container entries.

        GET /api/terminal/entries/customer-names/

        Returns: Array of distinct customer names (non-empty values only)
        """
        # Query distinct customer names, excluding empty strings and null values
        names = (
            ContainerEntry.objects.exclude(client_name__isnull=True)
            .exclude(client_name__exact="")
            .values_list("client_name", flat=True)
            .distinct()
            .order_by("client_name")
        )

        # Convert QuerySet to list
        names_list = list(names)

        # Return as wrapped response
        return Response(
            {"success": True, "data": names_list}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="upload-file",
    )
    def upload_file(self, request, pk=None):
        """
        Upload file and attach to this container entry.
        One-step convenience endpoint.
        """
        from apps.files.models import File, FileAttachment
        from apps.files.serializers import FileSerializer

        entry = self.get_object()

        # Get uploaded file
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            raise BusinessLogicError(
                message="No file provided",
                error_code="MISSING_FILE",
            )

        # Get parameters
        category = request.data.get("category", "container_image")
        attachment_type = request.data.get("attachment_type", "container_photo")
        description = request.data.get("description", "")
        is_public = request.data.get("is_public", "false").lower() == "true"

        # Create File using manager
        try:
            file_obj = File.objects.create_from_upload(
                uploaded_file=uploaded_file,
                category_code=category,
                user=request.user,
                is_public=is_public,
            )
        except ValueError as e:
            raise BusinessLogicError(
                message=str(e),
                error_code="FILE_ERROR",
            )

        # Attach to entry
        attachment = FileAttachment.objects.create(
            file=file_obj,
            content_object=entry,
            attachment_type=attachment_type,
            description=description,
        )

        # Return file details
        serializer = FileSerializer(file_obj, context={"request": request})
        return Response(
            {
                "success": True,
                "data": {
                    "file": serializer.data,
                    "attachment_id": attachment.id,
                    "attachment_type": attachment.attachment_type,
                    "description": attachment.description,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def files(self, request, pk=None):
        """Get all files attached to this container entry"""
        from django.contrib.contenttypes.models import ContentType

        from apps.files.models import FileAttachment
        from apps.files.serializers import FileSerializer

        entry = self.get_object()

        # Get content type for ContainerEntry
        content_type = ContentType.objects.get_for_model(entry)

        # Get all attachments
        attachments = FileAttachment.objects.filter(
            content_type=content_type, object_id=entry.id
        ).select_related("file")

        # Serialize
        data = []
        for attachment in attachments:
            file_serializer = FileSerializer(
                attachment.file, context={"request": request}
            )
            data.append(
                {
                    "attachment_id": attachment.id,
                    "attachment_type": attachment.attachment_type,
                    "description": attachment.description,
                    "display_order": attachment.display_order,
                    "file": file_serializer.data,
                }
            )

        return Response({"success": True, "data": data})

    @action(
        detail=True,
        methods=["delete"],
        url_path="remove-file/(?P<attachment_id>[0-9]+)",
    )
    def remove_file(self, request, pk=None, attachment_id=None):
        """Remove a file attachment from this container entry"""
        from django.contrib.contenttypes.models import ContentType

        from apps.files.models import FileAttachment

        entry = self.get_object()

        # Get content type for ContainerEntry
        content_type = ContentType.objects.get_for_model(entry)

        # Get the specific attachment
        try:
            attachment = FileAttachment.objects.get(
                id=attachment_id, content_type=content_type, object_id=entry.id
            )
        except FileAttachment.DoesNotExist:
            raise BusinessLogicError(
                message="Attachment not found",
                error_code="NOT_FOUND",
            )

        # Get the file before deleting attachment
        file_obj = attachment.file

        # Delete the attachment
        attachment.delete()

        # Check if file is used in other attachments
        other_attachments_exist = FileAttachment.objects.filter(file=file_obj).exists()

        # If file is not used anywhere else, soft delete it
        if not other_attachments_exist:
            file_obj.is_active = False
            file_obj.save(update_fields=["is_active"])

        return Response(
            {"success": True, "message": "File removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        url_path="import-excel",
    )
    def import_excel(self, request):
        """
        Import container entries from an Excel file.

        POST /api/terminal/entries/import-excel/
        Body: multipart/form-data with 'file' field

        Returns import statistics including success count, skipped, and errors.
        """
        # Validate file upload
        serializer = ContainerEntryImportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Invalid file upload",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get uploaded file
            uploaded_file = serializer.validated_data["file"]

            # Create import service
            import_service = ContainerEntryImportService()

            # Perform import
            result = import_service.import_from_excel(uploaded_file, request.user)

            # Return result
            if result["success"]:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Import failed: {e!s}",
                    "errors": [str(e)],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Export entries to Excel",
        description="Export container entries to an Excel file (.xlsx). Respects all applied filters, search, and ordering parameters.",
        parameters=[
            {
                "name": "container_owner_id",
                "in": "query",
                "description": "Filter by container owner ID (single ID or comma-separated). Example: 2 or 1,2,3",
                "required": False,
                "schema": {"type": "string"},
            },
            {
                "name": "container_owner_ids",
                "in": "query",
                "description": "Filter by container owner IDs (comma-separated, alias for container_owner_id). Example: 1,2,3",
                "required": False,
                "schema": {"type": "string"},
            },
            {
                "name": "client_name__icontains",
                "in": "query",
                "description": "Filter by client/customer name (partial match, case-insensitive)",
                "required": False,
                "schema": {"type": "string"},
            },
            {
                "name": "entry_date_after",
                "in": "query",
                "description": "Filter entries from this date (format: YYYY-MM-DD)",
                "required": False,
                "schema": {"type": "string", "format": "date"},
            },
            {
                "name": "entry_date_before",
                "in": "query",
                "description": "Filter entries until this date (format: YYYY-MM-DD)",
                "required": False,
                "schema": {"type": "string", "format": "date"},
            },
            {
                "name": "status",
                "in": "query",
                "description": "Filter by container status (EMPTY, LADEN or Russian: Порожний, Гружёный)",
                "required": False,
                "schema": {"type": "string"},
            },
            {
                "name": "search_text",
                "in": "query",
                "description": "Search across all fields (container, client, owner, cargo, location, etc.)",
                "required": False,
                "schema": {"type": "string"},
            },
        ],
        responses={
            200: bytes,
            400: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            },
            500: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            },
        },
    )
    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        """
        Export container entries to an Excel file.

        GET /api/terminal/entries/export-excel/

        Respects all applied filters, search, and ordering parameters.

        Key Query Parameters:
        - container_owner_ids: Filter by container owner IDs (comma-separated, e.g., "1,2,3")
        - client_name__icontains: Filter by customer/client name (partial match)
        - entry_date_after: Start date for date range filter (YYYY-MM-DD)
        - entry_date_before: End date for date range filter (YYYY-MM-DD)
        - status: Filter by container status (EMPTY, LADEN or Russian names)
        - search_text: Full-text search across all fields

        Examples:

        1. Export by date range:
        GET /api/terminal/entries/export_excel/?entry_date_after=2025-01-01&entry_date_before=2025-12-31

        2. Export by customer and container owners:
        GET /api/terminal/entries/export_excel/?client_name__icontains=ClientName&container_owner_ids=1,2,3

        3. Export with multiple filters:
        GET /api/terminal/entries/export_excel/?status=EMPTY&entry_date_after=2025-01-01&container_owner_ids=5&client_name__icontains=Client

        Returns: Excel file (.xlsx) with all container entry data in Russian columns.
        """
        try:
            # Get filtered queryset (respects all filters, search, and ordering)
            queryset = self.filter_queryset(self.get_queryset())

            # Create export service
            export_service = ContainerEntryExportService()

            # Generate Excel file
            excel_bytes = export_service.export_to_excel(queryset)

            # Generate filename with timestamp
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            filename = f"container_entries_{timestamp}.xlsx"

            # Wrap bytes in BytesIO for FileResponse
            buffer = io.BytesIO(excel_bytes)

            # Return file response
            response = FileResponse(
                buffer,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                filename=filename,
            )

            return response

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Export failed: {e!s}",
                    "errors": [str(e)],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PlateRecognizerAPIView(viewsets.GenericViewSet):
    """
    API endpoint for license plate recognition (public access for Telegram Mini App).
    Uses shared PlateRecognizerAPIService for plate recognition.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = PlateRecognitionRequestSerializer

    @property
    def plate_service(self):
        from apps.core.services.plate_recognizer_service import (
            PlateRecognizerAPIService,
        )

        return PlateRecognizerAPIService()

    @extend_schema(
        summary="Recognize license plate",
        request=PlateRecognitionRequestSerializer,
        responses={
            200: PlateRecognitionResponseSerializer,
            400: OpenApiResponse(description="Invalid request or image"),
            500: OpenApiResponse(description="Server error or API unavailable"),
        },
        description="""
        Recognize license plate number from uploaded image.

        Supports various image formats (JPEG, PNG, BMP, GIF).
        Uses PlateRecognizer.com API for accurate OCR recognition.
        """,
    )
    @action(detail=False, methods=["post"], url_path="recognize")
    def recognize(self, request):
        """POST /api/terminal/plate-recognizer/recognize/"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error_message": "Invalid request",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        image = serializer.validated_data["image"]
        region = serializer.validated_data.get("region", "uz")

        result = self.plate_service.recognize_plate(image.read(), region)

        response_data = {
            "success": result.success,
            "plate_number": result.plate_number,
            "confidence": result.confidence,
            "error_message": result.error_message,
        }

        return Response(
            response_data,
            status=status.HTTP_200_OK
            if result.success
            else status.HTTP_400_BAD_REQUEST,
        )


class PreOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for viewing customer pre-orders (admin access).
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["plate_number", "customer__first_name", "customer__phone_number"]
    ordering_fields = ["created_at", "status", "plate_number"]
    ordering = ["-created_at"]

    def get_queryset(self):
        from .models import PreOrder

        queryset = PreOrder.objects.select_related(
            "customer", "truck_photo", "matched_entry"
        ).all()

        # Filter by status
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        # Filter by customer
        customer_id = self.request.query_params.get("customer_id")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        # Filter by plate number (partial match)
        plate = self.request.query_params.get("plate_number")
        if plate:
            queryset = queryset.filter(plate_number__icontains=plate.upper())

        # Filter by operation type
        operation_type = self.request.query_params.get("operation_type")
        if operation_type:
            queryset = queryset.filter(operation_type=operation_type.upper())

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PreOrderListSerializer
        return PreOrderSerializer

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get all pending pre-orders (for gate matching)."""

        queryset = self.get_queryset().filter(status="PENDING")
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = PreOrderListSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = PreOrderListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get pre-order statistics."""
        from django.db.models import Count

        from .models import PreOrder

        stats = PreOrder.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=models.Q(status="PENDING")),
            matched=Count("id", filter=models.Q(status="MATCHED")),
            completed=Count("id", filter=models.Q(status="COMPLETED")),
            cancelled=Count("id", filter=models.Q(status="CANCELLED")),
        )

        return Response({"success": True, "data": stats})

    @action(detail=True, methods=["get"], url_path="match-info")
    def match_info(self, request, pk=None):
        """Get detailed matching info for a pre-order."""

        preorder = self.get_object()

        data = PreOrderSerializer(preorder, context={"request": request}).data

        # Add matched entry details if available
        if preorder.matched_entry:
            data["matched_entry_details"] = {
                "id": preorder.matched_entry.id,
                "container_number": preorder.matched_entry.container.container_number,
                "entry_time": preorder.matched_entry.entry_time,
                "status": preorder.matched_entry.get_status_display(),
            }

        return Response({"success": True, "data": data})

    @action(detail=False, methods=["get"], url_path="by-batch")
    def by_batch(self, request):
        """
        Get pre-orders grouped by batch_id.

        Returns orders grouped by their submission batch, making it easy to see
        which orders were submitted together by a customer.

        Query params:
            - customer_id: Filter by customer
            - status: Filter by status (PENDING, MATCHED, COMPLETED, CANCELLED)

        Response:
        {
            "success": true,
            "data": [
                {
                    "batch_id": "uuid...",
                    "customer": {"id": 1, "name": "..."},
                    "created_at": "2025-...",
                    "status": "PENDING",
                    "orders_count": 3,
                    "orders": [...]
                }
            ]
        }
        """
        from collections import OrderedDict

        # Get base queryset with filters applied
        queryset = (
            self.get_queryset().exclude(batch_id__isnull=True).order_by("-created_at")
        )

        # Group by batch_id
        batches = OrderedDict()
        for preorder in queryset:
            batch_key = str(preorder.batch_id)
            if batch_key not in batches:
                batches[batch_key] = {
                    "batch_id": preorder.batch_id,
                    "customer": {
                        "id": preorder.customer.id,
                        "name": preorder.customer.full_name,
                    }
                    if preorder.customer
                    else None,
                    "created_at": preorder.created_at,
                    "status": preorder.status,
                    "status_display": preorder.get_status_display(),
                    "orders_count": 0,
                    "orders": [],
                }
            batches[batch_key]["orders_count"] += 1
            batches[batch_key]["orders"].append(
                PreOrderSerializer(preorder, context={"request": request}).data
            )

        # Convert to list
        result = list(batches.values())

        return Response({"success": True, "data": result})


# ============ Placement ViewSet ============


class PlacementViewSet(viewsets.GenericViewSet):
    """
    ViewSet for 3D terminal container placement operations.

    Provides endpoints for:
    - Getting complete terminal layout for 3D visualization
    - Auto-suggesting optimal positions for containers
    - Assigning containers to positions
    - Moving containers between positions
    - Listing available positions
    - Listing unplaced containers
    """

    permission_classes = [IsAuthenticated]

    def get_placement_service(self):
        """Lazy-load PlacementService."""
        from apps.terminal_operations.services.placement_service import PlacementService

        return PlacementService()

    @extend_schema(
        summary="Get terminal layout for 3D visualization",
        description=(
            "Returns complete terminal data including all zones, dimensions, "
            "positioned containers, and occupancy statistics. "
            "Used by the frontend to render the 3D terminal view."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"$ref": "#/components/schemas/PlacementLayout"},
                },
            }
        },
        tags=["Placement"],
    )
    @action(detail=False, methods=["get"])
    def layout(self, request):
        """Get complete terminal layout for 3D visualization."""
        service = self.get_placement_service()
        data = service.get_layout()
        return Response({"success": True, "data": data})

    @extend_schema(
        summary="Auto-suggest position for container",
        description=(
            "Generates an optimal position suggestion for a container using "
            "a greedy algorithm that prioritizes ground-level slots and "
            "zones with the most availability."
        ),
        request=PlacementSuggestRequestSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"$ref": "#/components/schemas/PlacementSuggestResponse"},
                },
            }
        },
        tags=["Placement"],
    )
    @action(detail=False, methods=["post"])
    def suggest(self, request):
        """Auto-suggest optimal position for a container."""
        serializer = PlacementSuggestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self.get_placement_service()
        result = service.suggest_position(
            container_entry_id=serializer.validated_data["container_entry_id"],
            zone_preference=serializer.validated_data.get("zone_preference"),
        )

        return Response({"success": True, "data": result})

    @extend_schema(
        summary="Assign container to position",
        description=(
            "Assigns a container to a specific position in the terminal yard. "
            "Validates stacking rules (tier > 1 requires support below) and "
            "ensures the position is not already occupied."
        ),
        request=PlacementAssignRequestSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"$ref": "#/components/schemas/ContainerPosition"},
                    "message": {"type": "string"},
                },
            }
        },
        tags=["Placement"],
    )
    @action(detail=False, methods=["post"])
    def assign(self, request):
        """Assign container to a specific position."""
        serializer = PlacementAssignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        position_data = serializer.validated_data["position"]
        service = self.get_placement_service()

        position = service.assign_position(
            container_entry_id=serializer.validated_data["container_entry_id"],
            zone=position_data["zone"],
            row=position_data["row"],
            bay=position_data["bay"],
            tier=position_data["tier"],
            auto_assigned=False,
        )

        return Response(
            {
                "success": True,
                "data": ContainerPositionSerializer(position).data,
                "message": "Позиция успешно назначена",
            }
        )

    @extend_schema(
        summary="Move container to new position",
        description=(
            "Moves a container from its current position to a new one. "
            "Validates the new position is available and follows stacking rules."
        ),
        request=PlacementMoveRequestSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"$ref": "#/components/schemas/ContainerPosition"},
                    "message": {"type": "string"},
                },
            }
        },
        tags=["Placement"],
    )
    @action(detail=True, methods=["patch"], url_path="move")
    def move(self, request, pk=None):
        """Move container to a new position."""
        serializer = PlacementMoveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_position = serializer.validated_data["new_position"]
        service = self.get_placement_service()

        position = service.move_container(
            position_id=int(pk),
            new_zone=new_position["zone"],
            new_row=new_position["row"],
            new_bay=new_position["bay"],
            new_tier=new_position["tier"],
        )

        return Response(
            {
                "success": True,
                "data": ContainerPositionSerializer(position).data,
                "message": "Контейнер перемещён",
            }
        )

    @extend_schema(
        summary="Remove container from position",
        description=(
            "Removes a container from its position. "
            "Typically used when container exits the terminal."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            }
        },
        tags=["Placement"],
    )
    @action(detail=True, methods=["delete"], url_path="remove")
    def remove(self, request, pk=None):
        """Remove container from its position."""
        service = self.get_placement_service()
        service.remove_position(position_id=int(pk))

        return Response(
            {
                "success": True,
                "message": "Позиция освобождена",
            }
        )

    @extend_schema(
        summary="Get available positions",
        description=(
            "Returns list of available positions with optional filtering by zone and tier. "
            "Only returns positions that satisfy stacking rules."
        ),
        parameters=[
            OpenApiParameter(
                name="zone",
                type=str,
                enum=["A", "B", "C", "D", "E"],
                required=False,
                description="Filter by zone",
            ),
            OpenApiParameter(
                name="tier",
                type=int,
                required=False,
                description="Filter by tier (1-4)",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                required=False,
                description="Max positions to return (default 50)",
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Position"},
                    },
                    "count": {"type": "integer"},
                },
            }
        },
        tags=["Placement"],
    )
    @action(detail=False, methods=["get"])
    def available(self, request):
        """Get list of available positions."""
        zone = request.query_params.get("zone")
        tier = request.query_params.get("tier")
        limit = int(request.query_params.get("limit", 50))

        if tier:
            tier = int(tier)

        service = self.get_placement_service()
        positions = service.get_available_positions(
            zone=zone,
            tier=tier,
            limit=limit,
        )

        return Response(
            {
                "success": True,
                "data": positions,
                "count": len(positions),
            }
        )

    @extend_schema(
        summary="Get unplaced containers",
        description=(
            "Returns list of containers currently on terminal without an assigned position. "
            "These containers need to be placed via the assign endpoint."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/UnplacedContainer"},
                    },
                    "count": {"type": "integer"},
                },
            }
        },
        tags=["Placement"],
    )
    @action(detail=False, methods=["get"])
    def unplaced(self, request):
        """Get containers without assigned positions."""
        service = self.get_placement_service()
        containers = service.get_unplaced_containers()

        return Response(
            {
                "success": True,
                "data": containers,
                "count": len(containers),
            }
        )


# ============ Work Order ViewSet ============


class WorkOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for container placement work orders.

    Provides endpoints for:
    - Creating work orders (control room)
    - Assigning work orders to managers
    - Manager actions: accept, start, complete
    - Verification of completed placements
    - Listing active, pending, and overdue orders
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        """Return base queryset for work orders."""
        from .models import WorkOrder

        return WorkOrder.objects.select_related(
            "container_entry__container",
            "container_entry__company",
            "assigned_to_vehicle",
        ).order_by("-priority", "-created_at")

    def get_work_order_service(self):
        """Lazy-load WorkOrderService."""
        from apps.terminal_operations.services.work_order_service import (
            WorkOrderService,
        )

        return WorkOrderService()

    def _work_order_response(self, work_order, request, message: str):
        """Helper to create consistent work order response."""
        from .serializers import WorkOrderSerializer

        serializer = WorkOrderSerializer(work_order, context={"request": request})
        return Response(
            {
                "success": True,
                "data": serializer.data,
                "message": message,
            }
        )

    def _paginated_list_response(self, queryset, request):
        """Helper for paginated list responses."""
        from .serializers import WorkOrderListSerializer

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WorkOrderListSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = WorkOrderListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response({"success": True, "data": serializer.data})

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        from .serializers import (
            WorkOrderAssignSerializer,
            WorkOrderCompleteSerializer,
            WorkOrderCreateSerializer,
            WorkOrderFailSerializer,
            WorkOrderListSerializer,
            WorkOrderSerializer,
            WorkOrderVerifySerializer,
        )

        action_serializers = {
            "create": WorkOrderCreateSerializer,
            "assign": WorkOrderAssignSerializer,
            "complete": WorkOrderCompleteSerializer,
            "verify": WorkOrderVerifySerializer,
            "fail": WorkOrderFailSerializer,
        }
        if self.action in action_serializers:
            return action_serializers[self.action]
        if self.action == "list":
            return WorkOrderListSerializer
        return WorkOrderSerializer

    @extend_schema(
        summary="List work orders",
        description="List all active work orders. Filter by status, priority, or assigned manager.",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                required=False,
                description="Filter by status (comma-separated: PENDING,ASSIGNED,ACCEPTED,IN_PROGRESS,COMPLETED,VERIFIED,FAILED)",
            ),
            OpenApiParameter(
                name="assigned_to",
                type=int,
                required=False,
                description="Filter by assigned manager ID",
            ),
            OpenApiParameter(
                name="priority",
                type=str,
                required=False,
                description="Filter by priority (LOW,MEDIUM,HIGH,URGENT)",
            ),
        ],
        tags=["Work Orders"],
    )
    def list(self, request):
        """List work orders with optional filters."""
        queryset = self.get_queryset()

        # Apply filters
        status_param = request.query_params.get("status")
        if status_param:
            statuses = [s.strip().upper() for s in status_param.split(",")]
            queryset = queryset.filter(status__in=statuses)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        priority = request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority.upper())

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Get work order detail",
        description="Get detailed information about a specific work order.",
        tags=["Work Orders"],
    )
    def retrieve(self, request, pk=None):
        """Get single work order detail."""
        work_order = self.get_queryset().filter(id=pk).first()
        if not work_order:
            raise BusinessLogicError(
                message=f"Наряд #{pk} не найден",
                error_code="WORK_ORDER_NOT_FOUND",
            )

        serializer = self.get_serializer(work_order)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Create work order",
        description="Create a new placement work order. Position is auto-suggested if not provided.",
        tags=["Work Orders"],
    )
    def create(self, request):
        """Create a new work order."""
        from .serializers import WorkOrderSerializer

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self.get_work_order_service()
        work_order = service.create_work_order(
            container_entry_id=serializer.validated_data["container_entry_id"],
            zone=serializer.validated_data.get("zone"),
            row=serializer.validated_data.get("row"),
            bay=serializer.validated_data.get("bay"),
            tier=serializer.validated_data.get("tier"),
            sub_slot=serializer.validated_data.get("sub_slot", "A"),
            priority=serializer.validated_data.get("priority", "MEDIUM"),
            assigned_to_vehicle_id=serializer.validated_data.get("assigned_to_vehicle_id"),
            created_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )

        response_serializer = WorkOrderSerializer(
            work_order, context={"request": request}
        )
        return Response(
            {
                "success": True,
                "data": response_serializer.data,
                "message": "Наряд создан",
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Assign work order to vehicle",
        description="Assign a pending work order to a terminal vehicle.",
        tags=["Work Orders"],
    )
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign work order to a terminal vehicle."""
        from .serializers import WorkOrderSerializer

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self.get_work_order_service()
        work_order = service.assign_to_vehicle(
            work_order_id=int(pk),
            vehicle_id=serializer.validated_data["vehicle_id"],
        )

        response_serializer = WorkOrderSerializer(
            work_order, context={"request": request}
        )
        return Response(
            {
                "success": True,
                "data": response_serializer.data,
                "message": "Наряд назначен",
            }
        )

    @extend_schema(
        summary="Accept work order",
        description="Accept an assigned work order for a vehicle.",
        tags=["Work Orders"],
        parameters=[
            OpenApiParameter(
                name="vehicle_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Terminal vehicle ID accepting the order",
                required=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Accept the work order for a vehicle."""
        vehicle_id = request.query_params.get("vehicle_id")
        if not vehicle_id:
            raise BusinessLogicError(
                message="Не указан ID техники",
                error_code="VEHICLE_ID_REQUIRED",
            )

        service = self.get_work_order_service()
        work_order = service.accept_order(
            work_order_id=int(pk),
            vehicle_id=int(vehicle_id),
            operator=request.user if request.user.is_authenticated else None,
        )

        return self._work_order_response(work_order, request, "Наряд принят")

    @extend_schema(
        summary="Start work order",
        description="Start working on the work order (navigating to location).",
        tags=["Work Orders"],
        parameters=[
            OpenApiParameter(
                name="vehicle_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Terminal vehicle ID starting the order",
                required=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Start working on the order."""
        vehicle_id = request.query_params.get("vehicle_id")
        if not vehicle_id:
            raise BusinessLogicError(
                message="Не указан ID техники",
                error_code="VEHICLE_ID_REQUIRED",
            )

        service = self.get_work_order_service()
        work_order = service.start_order(
            work_order_id=int(pk),
            vehicle_id=int(vehicle_id),
            operator=request.user if request.user.is_authenticated else None,
        )

        return self._work_order_response(work_order, request, "Выполнение начато")

    @extend_schema(
        summary="Complete work order",
        description="Complete the work order with placement photo confirmation.",
        tags=["Work Orders"],
        parameters=[
            OpenApiParameter(
                name="vehicle_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Terminal vehicle ID completing the order",
                required=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete the work order with photo."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vehicle_id = request.query_params.get("vehicle_id")
        if not vehicle_id:
            raise BusinessLogicError(
                message="Не указан ID техники",
                error_code="VEHICLE_ID_REQUIRED",
            )

        service = self.get_work_order_service()
        work_order = service.complete_order(
            work_order_id=int(pk),
            vehicle_id=int(vehicle_id),
            operator=request.user if request.user.is_authenticated else None,
            placement_photo=serializer.validated_data.get("placement_photo"),
        )

        return self._work_order_response(work_order, request, "Размещение завершено")

    @extend_schema(
        summary="Verify placement",
        description="Control room verifies a completed placement (correct or incorrect).",
        tags=["Work Orders"],
    )
    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """Verify completed placement."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self.get_work_order_service()
        work_order = service.verify_placement(
            work_order_id=int(pk),
            is_correct=serializer.validated_data["is_correct"],
            notes=serializer.validated_data.get("notes", ""),
            verified_by=request.user,
        )

        return self._work_order_response(work_order, request, "Размещение проверено")

    @extend_schema(
        summary="Fail work order",
        description="Mark work order as failed with reason.",
        tags=["Work Orders"],
        parameters=[
            OpenApiParameter(
                name="vehicle_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Terminal vehicle ID reporting the failure (optional)",
                required=False,
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        """Mark work order as failed."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vehicle_id = request.query_params.get("vehicle_id")

        service = self.get_work_order_service()
        work_order = service.fail_order(
            work_order_id=int(pk),
            reason=serializer.validated_data["reason"],
            vehicle_id=int(vehicle_id) if vehicle_id else None,
        )

        return self._work_order_response(
            work_order, request, "Наряд отмечен как ошибочный"
        )

    @extend_schema(
        summary="Get vehicle work orders",
        description="Get work orders assigned to a specific terminal vehicle.",
        tags=["Work Orders"],
        parameters=[
            OpenApiParameter(
                name="vehicle_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Terminal vehicle ID to get orders for",
                required=True,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="vehicle-orders")
    def vehicle_orders(self, request):
        """Get work orders assigned to a specific vehicle."""
        vehicle_id = request.query_params.get("vehicle_id")
        if not vehicle_id:
            raise BusinessLogicError(
                message="Не указан ID техники",
                error_code="VEHICLE_ID_REQUIRED",
            )

        service = self.get_work_order_service()
        queryset = service.get_vehicle_orders(vehicle_id=int(vehicle_id))

        return self._paginated_list_response(queryset, request)

    @extend_schema(
        summary="Get my work orders (for Telegram Mini App)",
        description="Get work orders assigned to the vehicle operated by the user with the given telegram_id.",
        tags=["Work Orders"],
        parameters=[
            OpenApiParameter(
                name="telegram_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Telegram user ID of the operator",
                required=False,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="my-orders")
    def my_orders(self, request):
        """
        Get work orders for the current operator (identified by telegram_id).

        Looks up the user by telegram_id, finds their assigned vehicle,
        and returns active work orders for that vehicle.
        """
        from apps.accounts.models import CustomUser

        from .models import TerminalVehicle
        from .serializers import WorkOrderListSerializer

        telegram_id = request.query_params.get("telegram_id")

        # Find user by telegram_id (check both legacy field and profile)
        user = None
        if telegram_id:
            # Try legacy field first
            user = CustomUser.objects.filter(telegram_user_id=telegram_id).first()
            # If not found, try manager profile
            if not user:
                from apps.accounts.models import ManagerProfile

                profile = ManagerProfile.objects.filter(
                    telegram_user_id=telegram_id
                ).first()
                if profile:
                    user = profile.user

        # Find vehicle(s) operated by this user
        vehicles = []
        if user:
            vehicles = TerminalVehicle.objects.filter(
                operator=user, is_active=True
            ).values_list("id", flat=True)

        # If no vehicles found, return empty list
        if not vehicles:
            return Response(
                {
                    "success": True,
                    "count": 0,
                    "next": None,
                    "previous": None,
                    "results": [],
                }
            )

        # Get active work orders for these vehicles
        service = self.get_work_order_service()
        queryset = (
            service.get_queryset()
            if hasattr(service, "get_queryset")
            else self.get_queryset()
        )
        queryset = queryset.filter(
            assigned_to_vehicle_id__in=list(vehicles),
            status__in=["ASSIGNED", "ACCEPTED", "IN_PROGRESS"],
        ).order_by("-priority", "-created_at")

        # Return paginated response
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WorkOrderListSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = WorkOrderListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(
            {
                "success": True,
                "count": queryset.count(),
                "next": None,
                "previous": None,
                "results": serializer.data,
            }
        )

    @extend_schema(
        summary="Get pending work orders",
        description="Get unassigned work orders (for control room dashboard).",
        tags=["Work Orders"],
    )
    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get unassigned work orders."""
        service = self.get_work_order_service()
        queryset = service.get_pending_orders()

        return self._paginated_list_response(queryset, request)

    @extend_schema(
        summary="Get overdue work orders",
        description="Get work orders that have passed their SLA deadline.",
        tags=["Work Orders"],
    )
    @action(detail=False, methods=["get"])
    def overdue(self, request):
        """Get overdue work orders."""
        from .serializers import WorkOrderListSerializer

        service = self.get_work_order_service()
        queryset = service.get_overdue_orders()

        serializer = WorkOrderListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(
            {
                "success": True,
                "data": serializer.data,
                "count": queryset.count(),
            }
        )

    @extend_schema(
        summary="Get work order statistics",
        description="Get aggregated statistics about work orders.",
        tags=["Work Orders"],
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get work order statistics."""
        from django.db.models import Count, Q

        from .models import WorkOrder

        stats = WorkOrder.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="PENDING")),
            assigned=Count("id", filter=Q(status="ASSIGNED")),
            accepted=Count("id", filter=Q(status="ACCEPTED")),
            in_progress=Count("id", filter=Q(status="IN_PROGRESS")),
            completed=Count("id", filter=Q(status="COMPLETED")),
            verified=Count("id", filter=Q(status="VERIFIED")),
            failed=Count("id", filter=Q(status="FAILED")),
            overdue=Count(
                "id",
                filter=Q(
                    status__in=["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"],
                    sla_deadline__lt=timezone.now(),
                ),
            ),
        )

        return Response({"success": True, "data": stats})


class TerminalVehicleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for terminal vehicles (yard equipment).

    Provides full CRUD access to terminal vehicles for admin management
    and read-only access for work order assignment.
    """

    from .models import TerminalVehicle
    from .serializers import TerminalVehicleSerializer, TerminalVehicleWriteSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return all vehicles ordered by type and name.
        Includes inactive vehicles for admin management.
        """
        from .models import TerminalVehicle

        return TerminalVehicle.objects.select_related("operator").order_by(
            "vehicle_type", "name"
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        from .serializers import TerminalVehicleSerializer, TerminalVehicleWriteSerializer

        if self.action in ["create", "update", "partial_update"]:
            return TerminalVehicleWriteSerializer
        return TerminalVehicleSerializer

    def get_vehicle_service(self):
        """Lazy-load TerminalVehicleService."""
        from .services.terminal_vehicle_service import TerminalVehicleService

        return TerminalVehicleService()

    @extend_schema(
        summary="List terminal vehicles",
        description="Get all terminal vehicles for admin management.",
        tags=["Terminal Vehicles"],
    )
    def list(self, request, *args, **kwargs):
        """List all terminal vehicles."""
        from .serializers import TerminalVehicleSerializer

        queryset = self.get_queryset()
        serializer = TerminalVehicleSerializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
                "count": queryset.count(),
            }
        )

    @extend_schema(
        summary="Get terminal vehicle details",
        description="Get details for a specific terminal vehicle.",
        tags=["Terminal Vehicles"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Get terminal vehicle details."""
        from .serializers import TerminalVehicleSerializer

        instance = self.get_object()
        serializer = TerminalVehicleSerializer(instance)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Create terminal vehicle",
        description="Create a new terminal vehicle (yard equipment).",
        tags=["Terminal Vehicles"],
    )
    def create(self, request, *args, **kwargs):
        """Create a new terminal vehicle."""
        from .serializers import TerminalVehicleSerializer

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self.get_vehicle_service()
        vehicle = service.create_vehicle(
            name=serializer.validated_data["name"],
            vehicle_type=serializer.validated_data["vehicle_type"],
            license_plate=serializer.validated_data.get("license_plate", ""),
            operator_id=serializer.validated_data.get("operator_id"),
            is_active=serializer.validated_data.get("is_active", True),
        )

        response_serializer = TerminalVehicleSerializer(vehicle)
        return Response(
            {
                "success": True,
                "data": response_serializer.data,
                "message": "Техника успешно создана",
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Update terminal vehicle",
        description="Update an existing terminal vehicle.",
        tags=["Terminal Vehicles"],
    )
    def update(self, request, *args, **kwargs):
        """Update a terminal vehicle (full update)."""
        return self._perform_update(request, partial=False)

    @extend_schema(
        summary="Partial update terminal vehicle",
        description="Partially update an existing terminal vehicle.",
        tags=["Terminal Vehicles"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update a terminal vehicle."""
        return self._perform_update(request, partial=True)

    def _perform_update(self, request, partial: bool):
        """Shared update logic for PUT and PATCH."""
        from .serializers import TerminalVehicleSerializer

        instance = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        service = self.get_vehicle_service()

        # Determine if we should clear operator (operator_id is null in request)
        clear_operator = "operator_id" in request.data and request.data.get("operator_id") is None

        vehicle = service.update_vehicle(
            vehicle_id=instance.id,
            name=serializer.validated_data.get("name"),
            vehicle_type=serializer.validated_data.get("vehicle_type"),
            license_plate=serializer.validated_data.get("license_plate"),
            operator_id=serializer.validated_data.get("operator_id") if not clear_operator else None,
            is_active=serializer.validated_data.get("is_active"),
            clear_operator=clear_operator,
        )

        response_serializer = TerminalVehicleSerializer(vehicle)
        return Response(
            {
                "success": True,
                "data": response_serializer.data,
                "message": "Техника успешно обновлена",
            }
        )

    @extend_schema(
        summary="Delete terminal vehicle",
        description="Delete a terminal vehicle. Cannot delete vehicles with active work orders.",
        tags=["Terminal Vehicles"],
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a terminal vehicle."""
        instance = self.get_object()
        service = self.get_vehicle_service()
        service.delete_vehicle(vehicle_id=instance.id)

        return Response(
            {
                "success": True,
                "message": "Техника успешно удалена",
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Get available operators",
        description="Get list of managers who can be assigned as operators.",
        tags=["Terminal Vehicles"],
    )
    @action(detail=False, methods=["get"], url_path="operators")
    def operators(self, request):
        """Get list of available operators (managers)."""
        service = self.get_vehicle_service()
        operators = service.get_available_operators()

        data = [
            {"id": op.id, "full_name": op.full_name or op.username}
            for op in operators
        ]

        return Response(
            {
                "success": True,
                "data": data,
                "count": len(data),
            }
        )

    @extend_schema(
        summary="Get terminal vehicles with work status",
        description=(
            "Returns all terminal vehicles with computed work status. "
            "Used for sidebar display showing vehicles with operators and current work. "
            "Statuses: available (active with operator), working (has active order), offline (inactive/no operator)."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "count": {"type": "integer"},
                    "working_count": {"type": "integer"},
                },
            }
        },
        tags=["Terminal Vehicles"],
    )
    @action(detail=False, methods=["get"], url_path="with-status")
    def with_status(self, request):
        """
        Get all terminal vehicles with computed work status.

        Returns vehicles with:
        - operator_name: Full name of assigned operator
        - status: 'available', 'working', or 'offline'
        - current_task: Container number and target coordinate if working
        """
        from .models import TerminalVehicle
        from .serializers import TerminalVehicleStatusSerializer

        # Fetch all vehicles (not just active) with related data
        vehicles = (
            TerminalVehicle.objects.select_related("operator")
            .prefetch_related("work_orders__container_entry__container")
            .order_by("vehicle_type", "name")
        )

        serializer = TerminalVehicleStatusSerializer(vehicles, many=True)
        data = serializer.data

        # Count working vehicles
        working_count = sum(1 for v in data if v["status"] == "working")

        return Response(
            {
                "success": True,
                "data": data,
                "count": len(data),
                "working_count": working_count,
            }
        )
