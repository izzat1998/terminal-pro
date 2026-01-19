"""
API views for billing and storage cost functionality.
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.terminal_operations.models import ContainerEntry

from .models import Tariff
from apps.customer_portal.permissions import IsCustomer

from .serializers import (
    AvailablePeriodSerializer,
    BulkStorageCostRequestSerializer,
    BulkStorageCostResponseSerializer,
    MonthlyStatementSerializer,
    StorageCostResultSerializer,
    TariffCreateSerializer,
    TariffSerializer,
    TariffUpdateSerializer,
)
from .services import StatementExportService, StorageCostService
from .services.statement_service import MonthlyStatementService


class TariffViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tariffs.

    Provides CRUD operations for tariffs. Only admin users can manage tariffs.

    list: Get all tariffs (filterable by company, active status)
    create: Create a new tariff with rates
    retrieve: Get a specific tariff
    update: Update tariff (only effective_to and notes)
    destroy: Delete tariff (only if not referenced)
    """

    queryset = Tariff.objects.all().prefetch_related("rates").select_related("company")
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer_class(self):
        if self.action == "create":
            return TariffCreateSerializer
        elif self.action in ("update", "partial_update"):
            return TariffUpdateSerializer
        return TariffSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by company
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        elif self.request.query_params.get("general") == "true":
            queryset = queryset.filter(company__isnull=True)

        # Filter by active status
        active = self.request.query_params.get("active")
        if active == "true":
            queryset = queryset.filter(effective_to__isnull=True)
        elif active == "false":
            queryset = queryset.filter(effective_to__isnull=False)

        return queryset.order_by("-effective_from")

    def create(self, request, *args, **kwargs):
        """Create a new tariff with rates."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tariff = serializer.save()

        # Return the created tariff with full details
        response_serializer = TariffSerializer(tariff)
        return Response(
            {"success": True, "data": response_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        """Get a specific tariff with rates."""
        instance = self.get_object()
        serializer = TariffSerializer(instance)
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        """Update tariff (only effective_to and notes)."""
        instance = self.get_object()
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request, "instance": instance},
        )
        serializer.is_valid(raise_exception=True)
        serializer.update(instance, serializer.validated_data)

        response_serializer = TariffSerializer(instance)
        return Response({"success": True, "data": response_serializer.data})

    def destroy(self, request, *args, **kwargs):
        """Delete a tariff."""
        instance = self.get_object()

        # Prevent deletion if tariff might have been used in calculations
        # In the future, we could check for actual StorageCharge records
        if not instance.is_active and instance.effective_to:
            # Allow deletion of expired tariffs
            pass

        instance.delete()
        return Response(
            {"success": True, "message": "Тариф удален"},
            status=status.HTTP_200_OK,
        )

    def list(self, request, *args, **kwargs):
        """List all tariffs with optional filters."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = TariffSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TariffSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="company_id",
                description="Filter by company ID",
                required=False,
                type=int,
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get currently active tariffs."""
        queryset = self.get_queryset().filter(effective_to__isnull=True)

        company_id = request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        serializer = TariffSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="general")
    def general_tariffs(self, request):
        """Get general (default) tariffs."""
        queryset = self.get_queryset().filter(company__isnull=True)
        serializer = TariffSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})


class StorageCostView(APIView):
    """
    Calculate storage cost for a single container entry.

    GET /api/container-entries/{id}/storage-cost/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="as_of_date",
                description="Calculate up to this date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
        ],
        responses={200: StorageCostResultSerializer},
    )
    def get(self, request, entry_id):
        """Calculate storage cost for a container entry."""
        entry = get_object_or_404(
            ContainerEntry.objects.select_related("container", "company"),
            id=entry_id,
        )

        # Parse optional as_of_date
        as_of_date = None
        as_of_date_str = request.query_params.get("as_of_date")
        if as_of_date_str:
            from datetime import datetime

            try:
                as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_DATE",
                            "message": "Неверный формат даты. Используйте YYYY-MM-DD",
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        service = StorageCostService()
        result = service.calculate_cost(entry, as_of_date)

        serializer = StorageCostResultSerializer(result)
        return Response({"success": True, "data": serializer.data})


class BulkStorageCostView(APIView):
    """
    Calculate storage costs for multiple container entries.

    POST /api/storage-costs/calculate/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        request=BulkStorageCostRequestSerializer,
        responses={200: BulkStorageCostResponseSerializer},
    )
    def post(self, request):
        """Calculate storage costs for multiple containers."""
        serializer = BulkStorageCostRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        as_of_date = data.get("as_of_date")

        # Build queryset based on request
        if data.get("container_entry_ids"):
            entries = ContainerEntry.objects.filter(
                id__in=data["container_entry_ids"]
            ).select_related("container", "company")
        else:
            # Build from filters
            filters = data.get("filters", {})
            entries = ContainerEntry.objects.select_related("container", "company")

            if filters.get("company_id"):
                entries = entries.filter(company_id=filters["company_id"])

            if filters.get("status") == "active":
                entries = entries.filter(exit_date__isnull=True)
            elif filters.get("status") == "exited":
                entries = entries.filter(exit_date__isnull=False)

            if filters.get("entry_date_from"):
                entries = entries.filter(
                    entry_time__date__gte=filters["entry_date_from"]
                )
            if filters.get("entry_date_to"):
                entries = entries.filter(entry_time__date__lte=filters["entry_date_to"])

        # Calculate costs
        service = StorageCostService()
        results = service.calculate_bulk_costs(entries, as_of_date)

        # Build summary
        total_usd = sum(r.total_usd for r in results)
        total_uzs = sum(r.total_uzs for r in results)
        total_billable = sum(r.billable_days for r in results)

        response_data = {
            "results": [StorageCostResultSerializer(r).data for r in results],
            "summary": {
                "total_containers": len(results),
                "total_usd": total_usd,
                "total_uzs": total_uzs,
                "total_billable_days": total_billable,
            },
        }

        return Response({"success": True, "data": response_data})


class CustomerStorageCostView(APIView):
    """
    Customer view for their storage costs.

    GET /api/customer/storage-costs/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get storage costs for customer's company containers."""
        user = request.user

        # Get customer's company
        if hasattr(user, "customer_profile") and user.customer_profile.company:
            company = user.customer_profile.company
        elif user.company:
            company = user.company
        else:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "NO_COMPANY",
                        "message": "Пользователь не привязан к компании",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get active containers for the company
        entries = ContainerEntry.objects.filter(
            company=company,
            exit_date__isnull=True,
        ).select_related("container", "company")

        service = StorageCostService()
        results = service.calculate_bulk_costs(entries)

        # Build response
        active_containers = []
        for result in results:
            active_containers.append(
                {
                    "container_number": result.container_number,
                    "entry_date": result.entry_date,
                    "days_stored": result.total_days,
                    "current_cost_usd": result.total_usd,
                    "current_cost_uzs": result.total_uzs,
                }
            )

        total_usd = sum(r.total_usd for r in results)
        total_uzs = sum(r.total_uzs for r in results)

        return Response(
            {
                "success": True,
                "data": {
                    "active_containers": active_containers,
                    "summary": {
                        "total_active": len(results),
                        "total_current_cost_usd": total_usd,
                        "total_current_cost_uzs": total_uzs,
                    },
                },
            }
        )


class CustomerStatementView(APIView):
    """
    Get or generate a monthly statement for the authenticated customer's company.

    GET /api/customer/billing/statements/{year}/{month}/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        # Get customer's company
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = profile.company

        # Validate month
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for regenerate flag
        regenerate = request.query_params.get("regenerate", "").lower() == "true"

        # Get or generate statement
        service = MonthlyStatementService()
        statement = service.get_or_generate_statement(
            company=company,
            year=year,
            month=month,
            user=request.user,
            regenerate=regenerate,
        )

        serializer = MonthlyStatementSerializer(statement)
        return Response({"success": True, "data": serializer.data})


class CustomerStatementListView(APIView):
    """
    List all statements for the authenticated customer's company.

    GET /api/customer/billing/statements/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        year = request.query_params.get("year")
        service = MonthlyStatementService()
        statements = service.list_statements(
            company=profile.company,
            year=int(year) if year else None,
        )

        serializer = MonthlyStatementSerializer(statements, many=True)
        return Response({"success": True, "data": serializer.data})


class CustomerAvailablePeriodsView(APIView):
    """
    Get available billing periods for dropdown.

    GET /api/customer/billing/available-periods/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = MonthlyStatementService()
        periods = service.get_available_periods(profile.company)

        serializer = AvailablePeriodSerializer(periods, many=True)
        return Response({"success": True, "data": serializer.data})


class CustomerStatementExportExcelView(APIView):
    """
    Export statement to Excel.

    GET /api/customer/billing/statements/{year}/{month}/export/excel/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate month
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or generate statement
        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company,
            year=year,
            month=month,
            user=request.user,
        )

        # Export to Excel
        export_service = StatementExportService()
        excel_file = export_service.export_to_excel(statement)
        filename = export_service.get_excel_filename(statement)

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class CustomerStatementExportPdfView(APIView):
    """
    Export statement to PDF.

    GET /api/customer/billing/statements/{year}/{month}/export/pdf/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate month
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or generate statement
        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company,
            year=year,
            month=month,
            user=request.user,
        )

        # Export to PDF
        export_service = StatementExportService()
        pdf_file = export_service.export_to_pdf(statement)
        filename = export_service.get_pdf_filename(statement)

        response = HttpResponse(pdf_file.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
