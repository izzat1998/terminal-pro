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
