from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import BusinessLogicError
from apps.core.pagination import StandardResultsSetPagination

from .manager_views import IsAdminUser
from .models import Company
from .serializers import (
    CompanyCreateSerializer,
    CompanySerializer,
    CompanyStatsSerializer,
    CompanyUpdateSerializer,
    CustomerSerializer,
)
from .services import CompanyService


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing terminal customer companies.
    All endpoints require admin authentication.
    Detail views use slug for lookup (e.g., /companies/my-company/).
    """

    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination
    lookup_field = "slug"
    service = CompanyService()

    def get_queryset(self):
        """
        Get queryset with optional filtering.
        Annotates counts for efficient serialization.
        """
        from django.db.models import Count

        queryset = Company.objects.annotate(
            _customers_count=Count("customers", distinct=True),
            _entries_count=Count("container_entries", distinct=True),
        )

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Search by name or slug
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(slug__icontains=search))

        return queryset.order_by("name")

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == "create":
            return CompanyCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CompanyUpdateSerializer
        elif self.action == "stats":
            return CompanyStatsSerializer
        return CompanySerializer

    @extend_schema(
        summary="List companies",
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by active status",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search by name or slug",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (max 100)",
            ),
        ],
        responses={200: CompanySerializer(many=True)},
        description="List all companies with optional filtering and pagination",
    )
    def list(self, request):
        """
        List all companies with optional filtering and pagination.
        """
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "results": serializer.data})

    @extend_schema(
        summary="Get company",
        responses={
            200: CompanySerializer,
            404: OpenApiResponse(description="Company not found"),
        },
        description="Retrieve a company by slug",
    )
    def retrieve(self, request, slug=None):
        """
        Retrieve a company by slug.
        """
        company = self.get_object()
        serializer = self.get_serializer(company)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Create company",
        responses={
            201: CompanySerializer,
            400: OpenApiResponse(description="Invalid data or company already exists"),
            403: OpenApiResponse(description="Admin access required"),
        },
        description="Create a new company",
    )
    def create(self, request):
        """
        Create a new company (admin only).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            company = self.service.create_company(
                name=serializer.validated_data["name"],
            )

            return Response(
                {"success": True, "data": CompanySerializer(company).data},
                status=status.HTTP_201_CREATED,
            )
        except BusinessLogicError as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Update company",
        responses={
            200: CompanySerializer,
            400: OpenApiResponse(description="Invalid data"),
            404: OpenApiResponse(description="Company not found"),
        },
        description="Update company information by slug",
    )
    def update(self, request, slug=None, partial=False):
        """
        Update company information by slug (admin only).
        Supports both PUT (full update) and PATCH (partial update).
        """
        company = self.get_object()
        serializer = self.get_serializer(company, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_company = self.service.update_company(company_id=company.id, **serializer.validated_data)

            return Response({"success": True, "data": CompanySerializer(updated_company).data})
        except BusinessLogicError as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Deactivate company",
        request=None,
        responses={
            200: OpenApiResponse(description="Company deactivated (soft delete)"),
            404: OpenApiResponse(description="Company not found"),
        },
        description="Deactivate company by slug (soft delete)",
    )
    def destroy(self, request, slug=None):
        """
        Deactivate a company by slug (soft delete).
        Sets is_active=False instead of permanently deleting.
        """
        company = self.get_object()

        try:
            result = self.service.delete_company(company.id, hard_delete=False)
            return Response(
                {
                    "success": True,
                    "message": f"Компания '{result['name']}' деактивирована",
                }
            )
        except BusinessLogicError as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Activate company",
        request=None,
        responses={
            200: CompanySerializer,
            404: OpenApiResponse(description="Company not found"),
        },
        description="Activate a deactivated company by slug",
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, slug=None):
        """
        Activate a deactivated company by slug.
        """
        company = self.get_object()

        try:
            updated_company = self.service.update_company(company.id, is_active=True)
            return Response(
                {
                    "success": True,
                    "message": f"Компания '{updated_company.name}' активирована",
                    "data": CompanySerializer(updated_company).data,
                }
            )
        except BusinessLogicError as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Get company statistics",
        responses={200: CompanyStatsSerializer},
        description="Get company statistics",
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get statistics about companies.
        """
        total = Company.objects.count()
        active = Company.objects.filter(is_active=True).count()
        stats = {
            "total_companies": total,
            "active_companies": active,
            "inactive_companies": total - active,
        }

        serializer = CompanyStatsSerializer(stats)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Get company customers",
        responses={200: CustomerSerializer(many=True)},
        description="Get all customers belonging to this company",
    )
    @action(detail=True, methods=["get"])
    def customers(self, request, slug=None):
        """
        Get all customers belonging to this company.
        """
        from .models import CustomUser

        company = self.get_object()

        # Get customers from both profile and legacy fields
        customers = (
            CustomUser.objects.filter(user_type="customer")
            .filter(Q(customer_profile__company=company) | Q(customer_profile__isnull=True, company=company))
            .select_related("customer_profile", "customer_profile__company")
            .order_by("-created_at")
        )

        serializer = CustomerSerializer(customers, many=True)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Get company orders",
        responses={
            200: OpenApiResponse(description="All orders from company customers, grouped by batch"),
        },
        description="Get all pre-orders from company customers, grouped by batch_id",
    )
    @action(detail=True, methods=["get"])
    def orders(self, request, slug=None):
        """
        Get all pre-orders from company customers, grouped by batch_id.
        Each batch includes customer info for context.
        Orders without batch_id go to 'single_orders'.
        """
        from collections import OrderedDict

        from apps.terminal_operations.models import PreOrder
        from apps.terminal_operations.serializers import PreOrderSerializer

        from .models import CustomUser

        company = self.get_object()

        # Get all customers belonging to this company
        customer_ids = (
            CustomUser.objects.filter(user_type="customer")
            .filter(Q(customer_profile__company=company) | Q(customer_profile__isnull=True, company=company))
            .values_list("id", flat=True)
        )

        # Get all orders from these customers
        orders = (
            PreOrder.objects.filter(customer_id__in=customer_ids)
            .select_related("customer", "vehicle_entry", "matched_entry")
            .order_by("-created_at")
        )

        # Group orders by batch_id
        batches = OrderedDict()

        for order in orders:
            if order.batch_id:
                batch_key = str(order.batch_id)
                if batch_key not in batches:
                    batches[batch_key] = {
                        "batch_id": order.batch_id,
                        "created_at": order.created_at,
                        "customer_id": order.customer_id,
                        "customer_name": order.customer.full_name if order.customer else None,
                        "orders_count": 0,
                        "orders": [],
                    }
                batches[batch_key]["orders_count"] += 1
                batches[batch_key]["orders"].append(PreOrderSerializer(order, context={"request": request}).data)

        return Response({"success": True, "results": list(batches.values())})

    @extend_schema(
        summary="Get company container entries",
        parameters=[
            OpenApiParameter(
                name="search_text",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search across container number, client, cargo, notes, etc.",
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status (EMPTY/Порожний, LADEN/Гружёный)",
            ),
            OpenApiParameter(
                name="transport_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by transport type (TRUCK/Авто, WAGON/Вагон)",
            ),
            OpenApiParameter(
                name="has_exited",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by exit status (true/false)",
            ),
            OpenApiParameter(
                name="entry_date_after",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter entries after date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="entry_date_before",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter entries before date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sort by field (e.g., -entry_time, status, cargo_weight)",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (max 100)",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Paginated container entries with images"),
        },
        description="Get container entries linked to company customers with filtering, pagination, and file attachments",
    )
    @action(detail=True, methods=["get"])
    def entries(self, request, slug=None):
        """
        Get all container entries linked to company customers.
        Entries are found via PreOrder.matched_entry where customer belongs to company.

        Supports:
        - Pagination (page, page_size)
        - Filtering via ContainerEntryFilter (status, transport_type, dates, etc.)
        - Ordering (ordering=-entry_time)
        - Includes file attachments
        """
        from apps.terminal_operations.filters import ContainerEntryFilter
        from apps.terminal_operations.models import ContainerEntry
        from apps.terminal_operations.serializers import (
            ContainerEntryWithImagesSerializer,
        )

        from .models import CustomUser

        company = self.get_object()

        # Get all customer IDs belonging to this company
        customer_ids = (
            CustomUser.objects.filter(user_type="customer")
            .filter(Q(customer_profile__company=company) | Q(customer_profile__isnull=True, company=company))
            .values_list("id", flat=True)
        )

        # Get entries linked to company via:
        # 1. PreOrder from company's customer, OR
        # 2. Entry's company field matches directly
        queryset = (
            ContainerEntry.objects.filter(Q(pre_orders__customer_id__in=customer_ids) | Q(company=company))
            .select_related("container", "recorded_by", "container_owner", "company")
            .prefetch_related("crane_operations", "pre_orders")
            .distinct()
        )

        # Apply filters using ContainerEntryFilter
        filterset = ContainerEntryFilter(request.GET, queryset=queryset)
        queryset = filterset.qs

        # Apply ordering (default: -entry_time)
        ordering = request.query_params.get("ordering", "-entry_time")
        if ordering:
            queryset = queryset.order_by(ordering)

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ContainerEntryWithImagesSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        # Fallback without pagination
        serializer = ContainerEntryWithImagesSerializer(queryset, many=True, context={"request": request})
        return Response({"success": True, "results": serializer.data})

    # =========================================================================
    # Billing endpoints (mirror of customer billing)
    # =========================================================================

    @extend_schema(
        summary="Get company storage costs",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status: 'active' (on terminal), 'exited', or 'all'",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search by container number",
            ),
            OpenApiParameter(
                name="entry_date_from",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by entry date from (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="entry_date_to",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by entry date to (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Items per page (default: 20)",
            ),
        ],
        responses={200: OpenApiResponse(description="Storage costs with summary")},
        description="Get storage costs for all company containers with pagination and filtering",
    )
    @action(detail=True, methods=["get"], url_path="storage-costs")
    def storage_costs(self, request, slug=None):
        """
        Get storage costs for company containers (mirrors customer storage-costs endpoint).
        """
        from apps.billing.services.storage_cost_service import StorageCostService
        from apps.terminal_operations.models import ContainerEntry

        company = self.get_object()

        # Build base queryset
        entries = ContainerEntry.objects.filter(
            company=company,
        ).select_related("container", "company")

        # Apply filters
        status_filter = request.query_params.get("status")
        if status_filter == "active":
            entries = entries.filter(exit_date__isnull=True)
        elif status_filter == "exited":
            entries = entries.filter(exit_date__isnull=False)

        search = request.query_params.get("search", "").strip()
        if search:
            entries = entries.filter(container__container_number__icontains=search)

        entry_date_from = request.query_params.get("entry_date_from")
        if entry_date_from:
            entries = entries.filter(entry_time__date__gte=entry_date_from)

        entry_date_to = request.query_params.get("entry_date_to")
        if entry_date_to:
            entries = entries.filter(entry_time__date__lte=entry_date_to)

        # Order by entry time descending
        entries = entries.order_by("-entry_time")

        # Get total count before pagination
        total_count = entries.count()

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        offset = (page - 1) * page_size
        paginated_entries = entries[offset : offset + page_size]

        # Calculate costs for paginated entries
        cost_service = StorageCostService()
        cost_results = cost_service.calculate_bulk_costs(paginated_entries)

        # Build response items
        results = []
        for result in cost_results:
            results.append(
                {
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
                    "calculated_at": result.calculated_at.isoformat(),
                }
            )

        # Calculate summary for ALL matching entries (not just paginated)
        all_cost_results = cost_service.calculate_bulk_costs(entries) if total_count <= 500 else cost_results

        total_usd = sum(r.total_usd for r in all_cost_results)
        total_uzs = sum(r.total_uzs for r in all_cost_results)
        total_billable_days = sum(r.billable_days for r in all_cost_results)

        return Response(
            {
                "results": results,
                "count": total_count,
                "summary": {
                    "total_containers": len(all_cost_results) if total_count <= 500 else total_count,
                    "total_billable_days": total_billable_days,
                    "total_usd": str(total_usd),
                    "total_uzs": str(total_uzs),
                },
            }
        )

    @extend_schema(
        summary="List company billing statements",
        parameters=[
            OpenApiParameter(
                name="year",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by year",
            ),
        ],
        responses={200: OpenApiResponse(description="List of monthly statements")},
        description="List all monthly billing statements for the company",
    )
    @action(detail=True, methods=["get"], url_path="billing/statements")
    def billing_statements(self, request, slug=None):
        """
        List all monthly statements for the company.
        """
        from apps.billing.serializers import MonthlyStatementSerializer
        from apps.billing.services.statement_service import MonthlyStatementService

        company = self.get_object()

        year = request.query_params.get("year")
        statement_service = MonthlyStatementService()
        statements = statement_service.list_statements(
            company=company,
            year=int(year) if year else None,
        )

        serializer = MonthlyStatementSerializer(statements, many=True)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Get or generate company statement for a month",
        parameters=[
            OpenApiParameter(
                name="regenerate",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Force regenerate the statement",
            ),
        ],
        responses={200: OpenApiResponse(description="Monthly statement with line items")},
        description="Get or generate a monthly billing statement for the company",
    )
    @action(
        detail=True,
        methods=["get"],
        url_path=r"billing/statements/(?P<year>[0-9]+)/(?P<month>[0-9]+)",
    )
    def billing_statement_detail(self, request, slug=None, year=None, month=None):
        """
        Get or generate a monthly statement for the company.
        """
        from apps.billing.serializers import MonthlyStatementSerializer
        from apps.billing.services.statement_service import MonthlyStatementService

        company = self.get_object()
        year = int(year)
        month = int(month)

        # Validate month
        if not 1 <= month <= 12:
            return Response(
                {"success": False, "error": {"code": "INVALID_MONTH", "message": "Неверный месяц"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for regenerate flag
        regenerate = request.query_params.get("regenerate", "").lower() == "true"

        # Get or generate statement
        statement_service = MonthlyStatementService()
        statement = statement_service.get_or_generate_statement(
            company=company,
            year=year,
            month=month,
            user=request.user,
            regenerate=regenerate,
        )

        serializer = MonthlyStatementSerializer(statement)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Get available billing periods",
        responses={200: OpenApiResponse(description="List of available periods")},
        description="Get available billing periods for the company based on container entries",
    )
    @action(detail=True, methods=["get"], url_path="billing/available-periods")
    def billing_available_periods(self, request, slug=None):
        """
        Get available billing periods for the company.
        """
        from apps.terminal_operations.models import ContainerEntry

        company = self.get_object()

        # Get distinct year-month combinations from entries
        entries = ContainerEntry.objects.filter(company=company).order_by("-entry_time")

        periods = set()
        for entry in entries:
            periods.add((entry.entry_time.year, entry.entry_time.month))

        # Sort periods descending (newest first)
        sorted_periods = sorted(periods, reverse=True)

        # Format for dropdown
        result = []
        for year, month in sorted_periods:
            month_names = [
                "",
                "Январь",
                "Февраль",
                "Март",
                "Апрель",
                "Май",
                "Июнь",
                "Июль",
                "Август",
                "Сентябрь",
                "Октябрь",
                "Ноябрь",
                "Декабрь",
            ]
            result.append(
                {
                    "year": year,
                    "month": month,
                    "label": f"{month_names[month]} {year}",
                }
            )

        return Response({"success": True, "data": result})

    @extend_schema(
        summary="Get company additional charges",
        parameters=[
            OpenApiParameter(
                name="date_from",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by charge date from (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="date_to",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by charge date to (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search by container number",
            ),
        ],
        responses={200: OpenApiResponse(description="Additional charges with summary")},
        description="Get additional charges for company containers",
    )
    @action(detail=True, methods=["get"], url_path="additional-charges")
    def additional_charges(self, request, slug=None):
        """
        Get additional charges for company containers.
        """
        from django.db.models import Sum

        from apps.billing.models import AdditionalCharge
        from apps.billing.serializers import AdditionalChargeSerializer

        company = self.get_object()

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

        totals = queryset.aggregate(total_usd=Sum("amount_usd"), total_uzs=Sum("amount_uzs"))
        serializer = AdditionalChargeSerializer(queryset, many=True)

        return Response({
            "success": True,
            "data": serializer.data,
            "summary": {
                "total_charges": queryset.count(),
                "total_usd": str(totals["total_usd"] or 0),
                "total_uzs": str(totals["total_uzs"] or 0),
            },
        })
