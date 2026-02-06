"""
Customer ViewSet for admin management of customers.
"""

import logging

from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import BusinessLogicError

from .manager_views import IsAdminUser
from .models import CustomUser
from .serializers import (
    CustomerCreateSerializer,
    CustomerSerializer,
    CustomerStatsSerializer,
    CustomerUpdateSerializer,
)
from .services.customer_service import CustomerService


logger = logging.getLogger(__name__)


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customers.
    All endpoints require admin authentication.
    """

    permission_classes = [IsAdminUser]
    service = CustomerService()

    def get_queryset(self):
        """
        Get queryset with optional filtering.
        Uses select_related to prefetch profile data for better performance.
        Filters check both profile fields and legacy fields during migration.
        """
        from django.db.models import Count

        queryset = CustomUser.objects.filter(user_type="customer").select_related(
            "customer_profile", "customer_profile__company"
        ).annotate(
            _orders_count=Count("pre_orders"),
        )

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by bot access (check profile first, then legacy)
        bot_access = self.request.query_params.get("bot_access")
        if bot_access is not None:
            bot_val = bot_access.lower() == "true"
            queryset = queryset.filter(
                Q(customer_profile__bot_access=bot_val) |
                Q(customer_profile__isnull=True, bot_access=bot_val)
            )

        # Filter by telegram linked status (check profile first, then legacy)
        has_telegram = self.request.query_params.get("has_telegram")
        if has_telegram is not None:
            if has_telegram.lower() == "true":
                queryset = queryset.filter(
                    Q(customer_profile__telegram_user_id__isnull=False) |
                    Q(customer_profile__isnull=True, telegram_user_id__isnull=False)
                )
            else:
                queryset = queryset.filter(
                    Q(customer_profile__telegram_user_id__isnull=True) |
                    Q(customer_profile__isnull=True, telegram_user_id__isnull=True)
                )

        # Filter by company
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(
                Q(customer_profile__company_id=company_id) |
                Q(customer_profile__isnull=True, company_id=company_id)
            )

        # Search by name or phone (check profile first, then legacy)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(customer_profile__phone_number__icontains=search) |
                Q(customer_profile__telegram_username__icontains=search) |
                Q(customer_profile__isnull=True, phone_number__icontains=search) |
                Q(customer_profile__isnull=True, telegram_username__icontains=search)
            )

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == "create":
            return CustomerCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CustomerUpdateSerializer
        elif self.action == "stats":
            return CustomerStatsSerializer
        return CustomerSerializer

    @extend_schema(
        summary="Create customer",
        responses={
            201: CustomerSerializer,
            400: OpenApiResponse(description="Invalid data"),
            403: OpenApiResponse(description="Admin access required"),
        },
        description="Create a new customer",
    )
    def create(self, request):
        """
        Create a new customer (admin only).
        Requires company_id as customers must be linked to a company.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get company from validated data (company_id -> company via source='company')
        company = serializer.validated_data.get("company")
        if not company:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "COMPANY_REQUIRED",
                        "message": "Для клиентов необходимо указать company_id",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = self.service.create_customer(
                phone_number=serializer.validated_data["phone_number"],
                first_name=serializer.validated_data["first_name"],
                company_id=company.id,
                bot_access=serializer.validated_data.get("bot_access", False),
                is_active=serializer.validated_data.get("is_active", True),
            )

            return Response(
                {"success": True, "data": CustomerSerializer(customer).data},
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
        summary="Update customer",
        responses={
            200: CustomerSerializer,
            400: OpenApiResponse(description="Invalid data"),
            404: OpenApiResponse(description="Customer not found"),
        },
        description="Update customer information",
    )
    def update(self, request, pk=None, partial=False):
        """
        Update customer information (admin only).
        """
        customer = self.get_object()
        serializer = self.get_serializer(customer, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_customer = self.service.update_customer(
                customer_id=customer.id, **serializer.validated_data
            )

            return Response({"success": True, "data": CustomerSerializer(updated_customer).data})
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
        summary="Grant customer access",
        request=None,
        responses={
            200: CustomerSerializer,
            404: OpenApiResponse(description="Customer not found"),
        },
        description="Grant bot access to customer",
    )
    @action(detail=True, methods=["post"], url_path="grant-access")
    def grant_access(self, request, pk=None):
        """
        Grant bot access to a customer.
        """
        customer = self.get_object()
        self.service.grant_access(customer.id)
        customer.refresh_from_db()

        return Response(
            {
                "success": True,
                "message": f"Доступ предоставлен клиенту {customer.first_name}",
                "data": CustomerSerializer(customer).data,
            }
        )

    @extend_schema(
        summary="Revoke customer access",
        request=None,
        responses={
            200: CustomerSerializer,
            404: OpenApiResponse(description="Customer not found"),
        },
        description="Revoke bot access from customer",
    )
    @action(detail=True, methods=["post"], url_path="revoke-access")
    def revoke_access(self, request, pk=None):
        """
        Revoke bot access from a customer.
        """
        customer = self.get_object()
        self.service.revoke_access(customer.id)
        customer.refresh_from_db()

        return Response(
            {
                "success": True,
                "message": f"Доступ отозван у клиента {customer.first_name}",
                "data": CustomerSerializer(customer).data,
            }
        )

    @extend_schema(
        summary="Get customer statistics",
        responses={
            200: CustomerStatsSerializer,
        },
        description="Get customer statistics",
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get statistics about customers.
        Counts from both profiles and legacy fields during migration.
        """
        from apps.terminal_operations.models import PreOrder

        total = CustomUser.objects.filter(user_type="customer").count()
        active = CustomUser.objects.filter(user_type="customer", is_active=True).count()

        # Count customers with access (profile or legacy)
        with_access = CustomUser.objects.filter(
            user_type="customer", is_active=True
        ).filter(
            Q(customer_profile__bot_access=True) |
            Q(customer_profile__isnull=True, bot_access=True)
        ).count()

        # Count customers with telegram (profile or legacy)
        with_telegram = CustomUser.objects.filter(user_type="customer").filter(
            Q(customer_profile__telegram_user_id__isnull=False) |
            Q(customer_profile__isnull=True, telegram_user_id__isnull=False)
        ).count()

        stats = {
            "total_customers": total,
            "active_customers": active,
            "customers_with_access": with_access,
            "customers_with_telegram": with_telegram,
            "total_orders": PreOrder.objects.count(),
            "pending_orders": PreOrder.objects.filter(status="PENDING").count(),
        }

        serializer = CustomerStatsSerializer(stats)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Get customer orders",
        responses={
            200: OpenApiResponse(description="Customer's orders grouped by batch"),
            404: OpenApiResponse(description="Customer not found"),
        },
        description="Get all orders for a specific customer, grouped by batch_id",
    )
    @action(detail=True, methods=["get"])
    def orders(self, request, pk=None):
        """
        Get all pre-orders for a specific customer, grouped by batch_id.
        Orders without batch_id are grouped under 'single_orders'.
        """
        from collections import OrderedDict

        from apps.terminal_operations.serializers import PreOrderSerializer

        customer = self.get_object()
        orders = customer.pre_orders.select_related(
            "vehicle_entry", "matched_entry"
        ).order_by("-created_at")

        # Group orders by batch_id
        batches = OrderedDict()

        for order in orders:
            if order.batch_id:
                batch_key = str(order.batch_id)
                if batch_key not in batches:
                    batches[batch_key] = {
                        "batch_id": order.batch_id,
                        "created_at": order.created_at,
                        "orders_count": 0,
                        "orders": [],
                    }
                batches[batch_key]["orders_count"] += 1
                batches[batch_key]["orders"].append(
                    PreOrderSerializer(order, context={"request": request}).data
                )

        return Response({"success": True, "results": list(batches.values())})

    @extend_schema(
        summary="Get customer vehicle entries",
        responses={
            200: OpenApiResponse(description="Customer's vehicle entries list"),
            404: OpenApiResponse(description="Customer not found"),
        },
        description="Get all vehicle entries for a specific customer",
    )
    @action(detail=True, methods=["get"], url_path="vehicle-entries")
    def vehicle_entries(self, request, pk=None):
        """
        Get all vehicle entries for a specific customer.
        """
        from apps.vehicles.serializers import VehicleEntrySerializer

        customer = self.get_object()
        entries = customer.customer_vehicle_entries.all().order_by("-entry_time")

        return Response(
            {"success": True, "data": VehicleEntrySerializer(entries, many=True).data}
        )

    @extend_schema(
        summary="Delete customer",
        request=None,
        responses={
            204: OpenApiResponse(description="Customer deleted successfully"),
            404: OpenApiResponse(description="Customer not found"),
        },
        description="Delete customer permanently",
    )
    def destroy(self, request, pk=None):
        """
        Delete a customer permanently (hard delete).
        """
        customer = self.get_object()
        customer_name = customer.full_name
        customer_id = customer.id

        customer.delete()

        logger.info(f"Deleted customer: {customer_name} (ID: {customer_id})")

        return Response(status=status.HTTP_204_NO_CONTENT)
