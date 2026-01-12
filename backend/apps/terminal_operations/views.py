import io

from django.db import models
from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
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
    CraneOperationSerializer,
    PlateRecognitionRequestSerializer,
    PlateRecognitionResponseSerializer,
    PreOrderListSerializer,
    PreOrderSerializer,
)
from .services import (
    ContainerEntryExportService,
    ContainerEntryImportService,
    ContainerEntryService,
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

    def get_queryset(self):
        """
        Filter crane operations by container_entry_id if provided in query params.
        Optimize with select_related for performance.
        """
        queryset = CraneOperation.objects.select_related(
            "container_entry", "container_entry__container"
        ).all()
        entry_id = self.request.query_params.get("container_entry_id")
        if entry_id:
            queryset = queryset.filter(container_entry_id=entry_id)
        return queryset

    def perform_create(self, serializer):
        """
        Create crane operation with container_entry from request data or query params
        """
        entry_id = self.request.data.get(
            "container_entry_id"
        ) or self.request.query_params.get("container_entry_id")
        if not entry_id:
            raise BusinessLogicError(
                message="Необходимо указать ID записи контейнера",
                error_code="MISSING_PARAMETER",
            )

        try:
            entry = ContainerEntry.objects.get(id=entry_id)
        except ContainerEntry.DoesNotExist:
            raise BusinessLogicError(
                message=f"Запись контейнера с ID {entry_id} не найдена",
                error_code="NOT_FOUND",
            )

        serializer.save(container_entry=entry)

    @action(detail=False, methods=["post"], url_path="for-entry")
    def for_entry(self, request):
        """
        Create a crane operation for a specific container entry.
        POST /api/terminal/crane-operations/for-entry/
        Body: {"container_entry_id": 123, "operation_date": "2025-10-28T10:30:00Z"}
        """
        entry_id = request.data.get("container_entry_id")
        if not entry_id:
            raise BusinessLogicError(
                message="Необходимо указать ID записи контейнера",
                error_code="MISSING_PARAMETER",
            )

        try:
            entry = ContainerEntry.objects.get(id=entry_id)
        except ContainerEntry.DoesNotExist:
            raise BusinessLogicError(
                message=f"Запись контейнера с ID {entry_id} не найдена",
                error_code="NOT_FOUND",
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(container_entry=entry)

        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED
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
    # Disable PATCH - only allow PUT for full updates
    http_method_names = ["get", "post", "put", "delete", "head", "options", "trace"]
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
