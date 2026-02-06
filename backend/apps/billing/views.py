"""
API views for billing and storage cost functionality.
"""

from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.utils import safe_int_param
from apps.customer_portal.permissions import IsCustomer
from apps.terminal_operations.models import ContainerEntry

from .models import AdditionalCharge, ExpenseType, Tariff, TerminalSettings
from .serializers import (
    AdditionalChargeCreateSerializer,
    AdditionalChargeSerializer,
    AvailablePeriodSerializer,
    BulkStorageCostRequestSerializer,
    BulkStorageCostResponseSerializer,
    ExpenseTypeSerializer,
    MonthlyStatementListSerializer,
    MonthlyStatementSerializer,
    StorageCostResultSerializer,
    TariffCreateSerializer,
    TariffSerializer,
    TariffUpdateSerializer,
    TerminalSettingsSerializer,
)
from .services import AdditionalChargeService, ExpenseTypeService, StatementExportService, StorageCostService, TariffService
from .services.statement_service import MonthlyStatementService


def _get_customer_company(user):
    """
    Resolve the company for a customer user.

    Returns the company or None if not associated.
    """
    if hasattr(user, "customer_profile") and user.customer_profile.company:
        return user.customer_profile.company
    if getattr(user, "company", None):
        return user.company
    return None


def build_storage_cost_row(result, invoiced_entry_ids: set, billed_amounts: dict | None = None) -> dict:
    """Build a single storage-cost response row with invoiced flag and billed amounts."""
    billed = billed_amounts.get(result.container_entry_id) if billed_amounts else None
    billed_usd = billed["usd"] if billed else Decimal("0")
    billed_uzs = billed["uzs"] if billed else Decimal("0")
    return {
        "container_entry_id": result.container_entry_id,
        "container_number": result.container_number,
        "company_name": result.company_name,
        "container_size": result.container_size,
        "container_status": result.container_status,
        "entry_date": result.entry_date.isoformat(),
        "end_date": result.end_date.isoformat(),
        "is_active": result.is_active,
        "total_days": result.total_days,
        "free_days_applied": result.free_days_applied,
        "billable_days": result.billable_days,
        "total_usd": str(result.total_usd),
        "total_uzs": str(result.total_uzs),
        "billed_usd": str(billed_usd),
        "billed_uzs": str(billed_uzs),
        "unbilled_usd": str(result.total_usd - billed_usd),
        "unbilled_uzs": str(result.total_uzs - billed_uzs),
        "calculated_at": result.calculated_at.isoformat(),
        "is_on_demand_invoiced": result.container_entry_id in invoiced_entry_ids,
    }


def get_invoiced_entry_ids(container_entry_ids: list[int]) -> set[int]:
    """Return set of container_entry_ids that are in active on-demand invoices."""
    from .models import OnDemandInvoiceItem

    return set(
        OnDemandInvoiceItem.objects.filter(
            container_entry_id__in=container_entry_ids,
            invoice__status__in=["draft", "finalized", "paid"],
        ).values_list("container_entry_id", flat=True)
    )


def get_billed_amounts(container_entry_ids: list[int]) -> dict[int, dict]:
    """Sum billed USD/UZS per container entry from non-cancelled monthly statements."""
    from django.db.models import Sum

    from .models import StatementLineItem

    rows = (
        StatementLineItem.objects.filter(
            container_entry_id__in=container_entry_ids,
            statement__status__in=["draft", "finalized", "paid"],
        )
        .values("container_entry_id")
        .annotate(
            billed_usd=Sum("amount_usd"),
            billed_uzs=Sum("amount_uzs"),
        )
    )
    return {
        row["container_entry_id"]: {
            "usd": row["billed_usd"] or Decimal("0"),
            "uzs": row["billed_uzs"] or Decimal("0"),
        }
        for row in rows
    }


NO_COMPANY_RESPONSE = {
    "success": False,
    "error": {
        "code": "NO_COMPANY",
        "message": "Пользователь не привязан к компании",
    },
}


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

    queryset = Tariff.objects.all().prefetch_related("rates").select_related("company", "created_by")
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

        tariff_service = TariffService()
        tariff = tariff_service.create_tariff(
            data=serializer.validated_data, user=request.user
        )

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

        tariff_service = TariffService()
        tariff = tariff_service.update_tariff(
            tariff_id=instance.pk,
            data=serializer.validated_data,
            user=request.user,
        )

        response_serializer = TariffSerializer(tariff)
        return Response({"success": True, "data": response_serializer.data})

    def destroy(self, request, *args, **kwargs):
        """Delete a tariff."""
        instance = self.get_object()

        tariff_service = TariffService()
        tariff_service.delete_tariff(tariff_id=instance.pk, user=request.user)

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


class BulkGenerateDraftsView(APIView):
    """
    Generate draft statements for all companies with activity in a given month.

    POST /api/billing/generate-all-drafts/
    Body: {"year": 2026, "month": 1}
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        year = request.data.get("year")
        month = request.data.get("month")

        if not year or not month:
            return Response(
                {"success": False, "error": {"code": "MISSING_PARAMS", "message": "Укажите year и month"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        year, month = safe_int_param(year, default=0), safe_int_param(month, default=0)
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = MonthlyStatementService()
        statements = service.generate_all_drafts(year, month, request.user)

        serializer = MonthlyStatementListSerializer(statements, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": f"Сформировано {len(statements)} черновиков",
        })


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

        # Authorization: admins can access all entries, customers only their company's
        user = request.user
        is_admin = user.is_staff or getattr(user, "user_type", None) == "admin"
        if not is_admin:
            company = _get_customer_company(user)
            if not company or entry.company_id != company.id:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "code": "NOT_FOUND",
                            "message": "Запись не найдена",
                        },
                    },
                    status=status.HTTP_404_NOT_FOUND,
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
        data = serializer.data

        # Add billed/unbilled amounts from monthly statements
        billed = get_billed_amounts([entry.id]).get(entry.id)
        billed_usd = billed["usd"] if billed else Decimal("0")
        billed_uzs = billed["uzs"] if billed else Decimal("0")
        data["billed_usd"] = str(billed_usd)
        data["billed_uzs"] = str(billed_uzs)
        data["unbilled_usd"] = str(result.total_usd - billed_usd)
        data["unbilled_uzs"] = str(result.total_uzs - billed_uzs)

        return Response({"success": True, "data": data})


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


class CustomerBulkStorageCostView(APIView):
    """
    Calculate storage costs for multiple container entries (customer version).

    POST /api/customer/storage-costs/calculate/

    Only allows calculation for containers belonging to the customer's company.
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request):
        """Calculate storage costs for customer's containers."""
        company = _get_customer_company(request.user)
        if not company:
            return Response(NO_COMPANY_RESPONSE, status=status.HTTP_400_BAD_REQUEST)

        container_entry_ids = request.data.get("container_entry_ids", [])
        as_of_date_str = request.data.get("as_of_date")

        # Parse as_of_date if provided
        as_of_date = None
        if as_of_date_str:
            from datetime import datetime
            try:
                as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"success": False, "error": {"code": "INVALID_DATE", "message": "Неверный формат даты. Используйте YYYY-MM-DD"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Filter to only include containers from customer's company
        entries = ContainerEntry.objects.filter(
            id__in=container_entry_ids,
            company=company,  # Security: only company's containers
        ).select_related("container", "company")

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
                "total_usd": str(total_usd or 0),
                "total_uzs": str(total_uzs or 0),
                "total_billable_days": total_billable,
            },
        }

        return Response({"success": True, "data": response_data})


class CustomerStorageCostView(APIView):
    """
    Customer view for their storage costs with pagination and filtering.

    GET /api/customer/storage-costs/

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20)
        - status: 'active' (on terminal) or 'exited'
        - search: Search by container number
        - entry_date_from: Filter by entry date (YYYY-MM-DD)
        - entry_date_to: Filter by entry date (YYYY-MM-DD)
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        """Get storage costs for customer's company containers."""
        company = _get_customer_company(request.user)
        if not company:
            return Response(NO_COMPANY_RESPONSE, status=status.HTTP_400_BAD_REQUEST)

        # Build base queryset with shared filters
        from apps.billing.utils import filter_storage_cost_entries

        entries = ContainerEntry.objects.filter(
            company=company,
        ).select_related("container", "company")
        entries = filter_storage_cost_entries(entries, request.query_params)

        # Get total count before pagination
        total_count = entries.count()

        # Pagination
        from apps.core.utils import safe_int_param

        page = safe_int_param(request.query_params.get("page"), 1, min_val=1)
        page_size = safe_int_param(request.query_params.get("page_size"), 20, min_val=1, max_val=100)
        offset = (page - 1) * page_size
        paginated_entries = entries[offset : offset + page_size]

        # Calculate costs for paginated entries
        service = StorageCostService()
        cost_results = service.calculate_bulk_costs(paginated_entries)

        # Build response items with on-demand invoice flags
        entry_ids = [r.container_entry_id for r in cost_results]
        invoiced_entry_ids = get_invoiced_entry_ids(entry_ids)

        results = [build_storage_cost_row(r, invoiced_entry_ids) for r in cost_results]

        # Summary from the current page only -- avoids O(N) recalculation
        page_total_usd = sum(r.total_usd for r in cost_results)
        page_total_uzs = sum(r.total_uzs for r in cost_results)
        page_billable_days = sum(r.billable_days for r in cost_results)

        return Response(
            {
                "success": True,
                "results": results,
                "count": total_count,
                "summary": {
                    "total_containers": total_count,
                    "total_billable_days": page_billable_days,
                    "total_usd": str(page_total_usd),
                    "total_uzs": str(page_total_uzs),
                    "is_page_summary": True,
                },
            }
        )


class CustomerStorageCostExportView(APIView):
    """
    Export storage costs to Excel for the authenticated customer's company.

    GET /api/customer/storage-costs/export/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        """Export storage costs for customer's company containers."""
        from django.http import HttpResponse

        company = _get_customer_company(request.user)
        if not company:
            return Response(NO_COMPANY_RESPONSE, status=status.HTTP_400_BAD_REQUEST)

        from apps.billing.utils import filter_storage_cost_entries

        entries = ContainerEntry.objects.filter(
            company=company,
        ).select_related("container", "company")
        entries = filter_storage_cost_entries(entries, request.query_params)

        service = StorageCostService()
        cost_results = service.calculate_bulk_costs(entries)

        export_service = StatementExportService()
        excel_file = export_service.export_storage_costs_to_excel(cost_results, company.name)

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = f"storage_costs_{company.slug or 'company'}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


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

        from apps.core.utils import safe_int_param

        year = safe_int_param(request.query_params.get("year"), None)
        service = MonthlyStatementService()
        statements = service.list_statements(
            company=profile.company,
            year=year,
        )

        serializer = MonthlyStatementListSerializer(statements, many=True)
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


class CustomerStatementExportActView(APIView):
    """
    Export statement as formal Счёт-фактура (act) Excel.

    GET /api/customer/billing/statements/{year}/{month}/export/act/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company,
            year=year,
            month=month,
            user=request.user,
        )

        settings = TerminalSettings.load()
        export_service = StatementExportService()
        excel_file = export_service.export_to_schet_factura(
            statement, settings, exchange_rate=statement.exchange_rate,
        )
        filename = export_service.get_schet_factura_filename(statement)

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class CompanyStatementExportActView(APIView):
    """
    Export statement as formal Счёт-фактура (act) Excel — admin access via company slug.

    GET /api/billing/companies/{slug}/statements/{year}/{month}/export/act/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, slug: str, year: int, month: int):
        from apps.accounts.models import Company

        company = get_object_or_404(Company, slug=slug)

        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=company,
            year=year,
            month=month,
            user=request.user,
        )

        settings = TerminalSettings.load()
        export_service = StatementExportService()
        excel_file = export_service.export_to_schet_factura(
            statement, settings, exchange_rate=statement.exchange_rate,
        )
        filename = export_service.get_schet_factura_filename(statement)

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class CustomerStatementExportActPreviewView(APIView):
    """
    Export statement Счёт-фактура as PDF preview.

    GET /api/customer/billing/statements/{year}/{month}/export/act-preview/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company,
            year=year,
            month=month,
            user=request.user,
        )

        settings = TerminalSettings.load()
        export_service = StatementExportService()
        pdf_file = export_service.export_to_schet_factura_pdf(
            statement, settings, exchange_rate=statement.exchange_rate,
        )

        response = HttpResponse(pdf_file.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="act_preview.pdf"'
        return response


class CompanyStatementExportActPreviewView(APIView):
    """
    Export statement Счёт-фактура as PDF preview — admin access via company slug.

    GET /api/billing/companies/{slug}/statements/{year}/{month}/export/act-preview/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, slug: str, year: int, month: int):
        from apps.accounts.models import Company

        company = get_object_or_404(Company, slug=slug)

        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=company,
            year=year,
            month=month,
            user=request.user,
        )

        settings = TerminalSettings.load()
        export_service = StatementExportService()
        pdf_file = export_service.export_to_schet_factura_pdf(
            statement, settings, exchange_rate=statement.exchange_rate,
        )

        response = HttpResponse(pdf_file.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="act_preview.pdf"'
        return response


class CustomerStatementExportHtmlPreviewView(APIView):
    """
    Render statement as HTML table for preview (no WeasyPrint needed).

    GET /api/customer/billing/statements/{year}/{month}/export/html-preview/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        from django.template.loader import render_to_string

        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company, year=year, month=month, user=request.user,
        )

        line_items = statement.line_items.all()
        service_items = statement.service_items.all() if hasattr(statement, "service_items") else []

        storage_total_usd = sum(i.amount_usd for i in line_items)
        storage_total_uzs = sum(i.amount_uzs for i in line_items)
        services_total_usd = sum(s.amount_usd for s in service_items)
        services_total_uzs = sum(s.amount_uzs for s in service_items)

        html = render_to_string("billing/statement_html_preview.html", {
            "statement": statement,
            "line_items": line_items,
            "service_items": service_items,
            "storage_total_usd": storage_total_usd,
            "storage_total_uzs": storage_total_uzs,
            "services_total_usd": services_total_usd,
            "services_total_uzs": services_total_uzs,
        })
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class CompanyStatementExportHtmlPreviewView(APIView):
    """
    Render statement as HTML table for preview — admin access via company slug.

    GET /api/billing/companies/{slug}/statements/{year}/{month}/export/html-preview/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, slug: str, year: int, month: int):
        from django.template.loader import render_to_string

        from apps.accounts.models import Company

        company = get_object_or_404(Company, slug=slug)

        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=company, year=year, month=month, user=request.user,
        )

        line_items = statement.line_items.all()
        service_items = statement.service_items.all() if hasattr(statement, "service_items") else []

        storage_total_usd = sum(i.amount_usd for i in line_items)
        storage_total_uzs = sum(i.amount_uzs for i in line_items)
        services_total_usd = sum(s.amount_usd for s in service_items)
        services_total_uzs = sum(s.amount_uzs for s in service_items)

        html = render_to_string("billing/statement_html_preview.html", {
            "statement": statement,
            "line_items": line_items,
            "service_items": service_items,
            "storage_total_usd": storage_total_usd,
            "storage_total_uzs": storage_total_uzs,
            "services_total_usd": services_total_usd,
            "services_total_uzs": services_total_uzs,
        })
        return HttpResponse(html, content_type="text/html; charset=utf-8")


def _render_act_html_preview(statement, settings_obj):
    """Render Счёт-фактура as HTML preview (shared by customer and admin views)."""
    import calendar

    from django.template.loader import render_to_string

    from .services.export_service import StatementExportService

    rate = statement.exchange_rate or settings_obj.default_usd_uzs_rate or Decimal("0")
    export_service = StatementExportService()

    grouped = export_service._group_line_items(statement)
    service_grouped = export_service._group_service_items(statement)
    vat_rate = settings_obj.vat_rate or Decimal("12")

    # Act date = last day of the billing month
    last_day = calendar.monthrange(statement.year, statement.month)[1]
    act_date = f"{last_day:02d}.{statement.month:02d}.{statement.year} г."

    item_no = 0
    grand_total_usd = Decimal("0")
    grand_total_uzs = Decimal("0")
    grand_vat_usd = Decimal("0")
    grand_vat_uzs = Decimal("0")

    grouped_items = []
    for label, total_usd, qty, unit, period_start, period_end in grouped:
        item_no += 1
        total_uzs = total_usd * rate
        # НДС inclusive: extract VAT from the total
        vat_usd = total_usd * vat_rate / (Decimal("100") + vat_rate)
        vat_uzs = total_uzs * vat_rate / (Decimal("100") + vat_rate)
        grand_total_usd += total_usd
        grand_total_uzs += total_uzs
        grand_vat_usd += vat_usd
        grand_vat_uzs += vat_uzs
        grouped_items.append({
            "number": item_no, "label": label, "unit": unit, "qty": qty,
            "unit_price_usd": f"{total_usd / qty if qty else 0:,.2f}",
            "total_usd": f"{total_usd:,.2f}", "vat_usd": f"{vat_usd:,.2f}",
            "total_with_vat_usd": f"{total_usd:,.2f}",
            "unit_price_uzs": f"{total_uzs / qty if qty else 0:,.0f}",
            "total_uzs": f"{total_uzs:,.0f}", "vat_uzs": f"{vat_uzs:,.0f}",
            "total_with_vat_uzs": f"{total_uzs:,.0f}",
            "period_start": period_start, "period_end": period_end,
        })

    svc_items = []
    for desc, svc_total_usd, svc_qty, svc_unit in service_grouped:
        item_no += 1
        svc_total_uzs = svc_total_usd * rate
        svc_vat_usd = svc_total_usd * vat_rate / (Decimal("100") + vat_rate)
        svc_vat_uzs = svc_total_uzs * vat_rate / (Decimal("100") + vat_rate)
        grand_total_usd += svc_total_usd
        grand_total_uzs += svc_total_uzs
        grand_vat_usd += svc_vat_usd
        grand_vat_uzs += svc_vat_uzs
        svc_items.append({
            "number": item_no, "label": desc, "unit": svc_unit, "qty": svc_qty,
            "unit_price_usd": f"{svc_total_usd / svc_qty if svc_qty else 0:,.2f}",
            "total_usd": f"{svc_total_usd:,.2f}", "vat_usd": f"{svc_vat_usd:,.2f}",
            "total_with_vat_usd": f"{svc_total_usd:,.2f}",
            "unit_price_uzs": f"{svc_total_uzs / svc_qty if svc_qty else 0:,.0f}",
            "total_uzs": f"{svc_total_uzs:,.0f}", "vat_uzs": f"{svc_vat_uzs:,.0f}",
            "total_with_vat_uzs": f"{svc_total_uzs:,.0f}",
        })

    # Format contract date if available
    contract_date_formatted = ""
    if statement.company.contract_date:
        contract_date_formatted = statement.company.contract_date.strftime("%d.%m.%Y г.")

    return render_to_string("billing/schet_factura_html_preview.html", {
        "statement": statement,
        "settings": settings_obj,
        "act_date": act_date,
        "contract_date_formatted": contract_date_formatted,
        "exchange_rate": f"{rate:,.2f}",
        "grouped_items": grouped_items,
        "service_items": svc_items,
        "grand_total_usd": f"{grand_total_usd:,.2f}",
        "grand_total_uzs": f"{grand_total_uzs:,.0f}",
        "grand_vat_usd": f"{grand_vat_usd:,.2f}",
        "grand_vat_uzs": f"{grand_vat_uzs:,.0f}",
        "grand_total_with_vat_usd": f"{grand_total_usd:,.2f}",
        "grand_total_with_vat_uzs": f"{grand_total_uzs:,.0f}",
    })


class CustomerStatementExportActHtmlPreviewView(APIView):
    """
    Render Счёт-фактура as HTML table for preview.

    GET /api/customer/billing/statements/{year}/{month}/export/act-html-preview/
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, year: int, month: int):
        profile = request.user.get_profile()
        if not profile or not profile.company:
            return Response(
                {"success": False, "error": {"code": "NO_COMPANY", "message": "Компания не найдена"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=profile.company, year=year, month=month, user=request.user,
        )
        settings_obj = TerminalSettings.load()
        html = _render_act_html_preview(statement, settings_obj)
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class CompanyStatementExportActHtmlPreviewView(APIView):
    """
    Render Счёт-фактура as HTML table for preview — admin access via company slug.

    GET /api/billing/companies/{slug}/statements/{year}/{month}/export/act-html-preview/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, slug: str, year: int, month: int):
        from apps.accounts.models import Company

        company = get_object_or_404(Company, slug=slug)
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=company, year=year, month=month, user=request.user,
        )
        settings_obj = TerminalSettings.load()
        html = _render_act_html_preview(statement, settings_obj)
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class AdditionalChargeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing additional charges (admin only)."""

    queryset = AdditionalCharge.objects.all().select_related(
        "container_entry__container",
        "container_entry__company",
        "created_by",
    )
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = None  # Disable pagination - charges are fetched per container

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AdditionalChargeCreateSerializer
        return AdditionalChargeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        container_entry_id = self.request.query_params.get("container_entry_id")
        container_entry_ids = self.request.query_params.get("container_entry_ids")
        if container_entry_ids:
            ids = [int(x) for x in container_entry_ids.split(",") if x.strip().isdigit()]
            if ids:
                queryset = queryset.filter(container_entry_id__in=ids)
        elif container_entry_id:
            queryset = queryset.filter(container_entry_id=container_entry_id)

        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(container_entry__company_id=company_id)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(charge_date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(charge_date__lte=date_to)

        return queryset.order_by("-charge_date", "-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AdditionalChargeService()
        charge = service.create_charge(
            data=serializer.validated_data, user=request.user
        )
        response_serializer = AdditionalChargeSerializer(charge)
        return Response(
            {"success": True, "data": response_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        service = AdditionalChargeService()
        charge = service.update_charge(
            charge_id=instance.id,
            data=serializer.validated_data,
            user=request.user,
        )
        response_serializer = AdditionalChargeSerializer(charge)
        return Response({"success": True, "data": response_serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        service = AdditionalChargeService()
        service.delete_charge(charge_id=instance.id, user=request.user)
        return Response({"success": True, "message": "Начисление удалено"}, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AdditionalChargeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AdditionalChargeSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        serializer = AdditionalChargeSerializer(self.get_object())
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["post"], url_path="bulk-summary")
    def bulk_summary(self, request):
        """
        Get summary of additional charges for multiple container entries.

        POST /api/billing/additional-charges/bulk-summary/
        Body: {"container_entry_ids": [1, 2, 3, ...]}

        Returns summary (total_usd, total_uzs, count) per container entry.
        """
        container_entry_ids = request.data.get("container_entry_ids", [])
        if not container_entry_ids:
            return Response(
                {"success": False, "error": {"code": "MISSING_IDS", "message": "Параметр container_entry_ids обязателен"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db.models import Sum, Count

        # Get aggregated sums per container entry
        summaries = (
            AdditionalCharge.objects.filter(container_entry_id__in=container_entry_ids)
            .values("container_entry_id")
            .annotate(
                total_usd=Sum("amount_usd"),
                total_uzs=Sum("amount_uzs"),
                charge_count=Count("id"),
            )
        )

        # Build response map
        results = []
        summary_map = {s["container_entry_id"]: s for s in summaries}

        for entry_id in container_entry_ids:
            summary = summary_map.get(entry_id)
            results.append({
                "container_entry_id": entry_id,
                "total_usd": str(summary["total_usd"]) if summary else "0.00",
                "total_uzs": str(summary["total_uzs"]) if summary else "0",
                "charge_count": summary["charge_count"] if summary else 0,
            })

        return Response({"success": True, "data": results})


class CustomerAdditionalChargeView(APIView):
    """
    Customer view for their additional charges (read-only) with pagination.

    GET /api/customer/billing/additional-charges/

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - date_from: Filter by charge date (YYYY-MM-DD)
        - date_to: Filter by charge date (YYYY-MM-DD)
        - search: Search by container number
    """

    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        company = _get_customer_company(request.user)
        if not company:
            return Response(NO_COMPANY_RESPONSE, status=status.HTTP_400_BAD_REQUEST)

        queryset = AdditionalCharge.objects.filter(
            container_entry__company=company
        ).select_related(
            "container_entry__container",
            "container_entry__company",
            "created_by",
        ).order_by("-charge_date", "-created_at")

        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(charge_date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(charge_date__lte=date_to)

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(container_entry__container__container_number__icontains=search)

        # Compute totals across the full filtered queryset (before pagination)
        from django.db.models import Sum
        totals = queryset.aggregate(total_usd=Sum("amount_usd"), total_uzs=Sum("amount_uzs"))
        total_count = queryset.count()

        # Pagination
        from apps.core.utils import safe_int_param

        page = safe_int_param(request.query_params.get("page"), 1, min_val=1)
        page_size = safe_int_param(request.query_params.get("page_size"), 20, min_val=1, max_val=100)
        offset = (page - 1) * page_size
        paginated_qs = queryset[offset : offset + page_size]

        serializer = AdditionalChargeSerializer(paginated_qs, many=True)

        return Response({
            "success": True,
            "data": serializer.data,
            "count": total_count,
            "summary": {
                "total_charges": total_count,
                "total_usd": str(totals["total_usd"] or 0),
                "total_uzs": str(totals["total_uzs"] or 0),
            },
        })


class ExpenseTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing expense types (admin only)."""

    queryset = ExpenseType.objects.all()
    serializer_class = ExpenseTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expense_type_service = ExpenseTypeService()

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by active status if requested
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense_type = self.expense_type_service.create_expense_type(
            data=serializer.validated_data, user=request.user
        )
        return Response(
            {"success": True, "data": ExpenseTypeSerializer(expense_type).data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        expense_type = self.expense_type_service.update_expense_type(
            expense_type_id=instance.pk, data=serializer.validated_data, user=request.user
        )
        return Response(
            {"success": True, "data": ExpenseTypeSerializer(expense_type).data}
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.expense_type_service.delete_expense_type(
            expense_type_id=instance.pk, user=request.user
        )
        return Response(
            {"success": True, "message": "Тип расхода удален"},
            status=status.HTTP_200_OK,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response({"success": True, "data": serializer.data})


class TerminalSettingsView(APIView):
    """
    GET/PUT terminal operator settings (singleton).

    Admin-only. Used for Счёт-фактура generation and formal documents.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        settings = TerminalSettings.load()
        serializer = TerminalSettingsSerializer(settings)
        return Response({"success": True, "data": serializer.data})

    def put(self, request):
        settings = TerminalSettings.load()
        serializer = TerminalSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": serializer.data})


class ExchangeRateView(APIView):
    """
    GET /api/billing/exchange-rate/?date=YYYY-MM-DD

    Returns the CBU exchange rate for a given date.
    Checks local cache first; fetches from cbu.uz if not cached.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        from datetime import datetime

        from apps.billing.services import cbu_service

        date_str = request.query_params.get("date")
        if not date_str:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_DATE",
                        "message": "Укажите параметр date (YYYY-MM-DD)",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
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

        try:
            rate = cbu_service.get_rate(target_date)
        except cbu_service.CBUServiceError as exc:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "CBU_FETCH_ERROR",
                        "message": str(exc),
                    },
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "currency": "USD",
                    "date": date_str,
                    "rate": str(rate),
                },
            }
        )
