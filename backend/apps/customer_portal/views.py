"""
ViewSets for customer portal API endpoints.

These viewsets provide thin wrappers around existing services,
applying customer-specific permissions and automatic data filtering.
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from apps.core.exceptions import BusinessLogicError
from apps.terminal_operations.filters import ContainerEntryFilter
from apps.terminal_operations.models import ContainerEntry, PreOrder
from apps.terminal_operations.services.preorder_service import PreOrderService

from .permissions import IsCustomer, IsCustomerOwner
from .serializers import (
    CustomerContainerEntrySerializer,
    CustomerPreOrderCreateSerializer,
    CustomerPreOrderSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Customer Profile"],
        summary="Get customer profile",
        description="Retrieve the authenticated customer's profile information including company details.",
        responses={200: CustomerProfileSerializer},
    ),
    update_profile=extend_schema(
        tags=["Customer Profile"],
        summary="Update customer profile",
        description="Update customer profile fields (first_name, last_name) or change password.",
        request=CustomerProfileUpdateSerializer,
        responses={200: CustomerProfileSerializer},
    ),
    company_members=extend_schema(
        tags=["Customer Profile"],
        summary="Get company members",
        description="Retrieve all customer users belonging to the same company as the authenticated user.",
        responses={200: CustomerProfileSerializer(many=True)},
    ),
    statistics=extend_schema(
        tags=["Customer Profile"],
        summary="Get company container statistics",
        description="Retrieve statistics about containers on terminal for the customer's company including status breakdown, dwell time metrics, and cargo summary.",
    ),
)
class CustomerProfileViewSet(viewsets.ViewSet):
    """
    ViewSet for customer profile management.

    Customers can view and update their own profile.
    """

    permission_classes = [IsCustomer]

    def _get_user_company(self, user):
        """Get the company associated with the user."""
        try:
            return user.customer_profile.company
        except Exception:
            if hasattr(user, "company"):
                return user.company
        return None

    def list(self, request):
        """
        Get current customer's profile.
        """
        serializer = CustomerProfileSerializer(request.user)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["patch", "put"])
    def update_profile(self, request):
        """
        Update customer profile (first_name, last_name, password).
        """
        serializer = CustomerProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Update the user instance
        updated_user = serializer.update(request.user, serializer.validated_data)

        # Return updated profile
        response_serializer = CustomerProfileSerializer(updated_user)
        return Response({"success": True, "data": response_serializer.data})

    @action(detail=False, methods=["get"])
    def company_members(self, request):
        """
        Get all customer users in the same company.
        """
        from apps.accounts.models import CustomUser

        company = self._get_user_company(request.user)
        if not company:
            return Response(
                {
                    "success": True,
                    "count": 0,
                    "company": None,
                    "data": [],
                }
            )

        # Get all customers in the same company
        customer_users = (
            CustomUser.objects.filter(
                user_type="customer",
                customer_profile__company=company,
            )
            .select_related("customer_profile")
            .order_by("-created_at")
        )

        serializer = CustomerProfileSerializer(customer_users, many=True)
        return Response(
            {
                "success": True,
                "count": customer_users.count(),
                "company": {
                    "id": company.id,
                    "name": company.name,
                    "slug": company.slug,
                },
                "data": serializer.data,
            }
        )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Get container statistics for customer's company.
        """
        company = self._get_user_company(request.user)
        if not company:
            return Response(
                {"success": False, "error": "No company found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .services.statistics_service import CustomerStatisticsService

        service = CustomerStatisticsService(company)
        stats = service.get_all_statistics()

        return Response({"success": True, "data": stats})


@extend_schema_view(
    list=extend_schema(
        tags=["Customer Containers"],
        summary="List company containers",
        description="List all container entries for the customer's company with comprehensive filtering support. "
        "Supports filters: status, transport_type, dates, container owner, cargo weight, dwell time, and more.",
        responses={200: CustomerContainerEntrySerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Customer Containers"],
        summary="Get container entry details",
        description="Retrieve detailed information about a specific container entry belonging to the customer's company.",
        responses={200: CustomerContainerEntrySerializer},
    ),
)
class CustomerContainerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for container entries (customer view).

    Customers can list and view their company's containers.
    Supports all existing filters from ContainerEntryFilter.
    """

    permission_classes = [IsCustomer]
    serializer_class = CustomerContainerEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ContainerEntryFilter
    ordering_fields = ["entry_time", "exit_date", "dwell_time_days"]
    ordering = ["-entry_time"]  # Newest first by default

    def get_queryset(self):
        """
        Get container entries filtered by customer's company.
        Automatically filters by company - customers can ONLY see their company's data.
        """
        # Get customer's company
        customer_company = None
        try:
            customer_company = self.request.user.customer_profile.company
        except Exception:
            if hasattr(self.request.user, "company"):
                customer_company = self.request.user.company

        if not customer_company:
            return ContainerEntry.objects.none()

        # Filter by company and optimize query
        return (
            ContainerEntry.objects.filter(company=customer_company)
            .select_related("container", "recorded_by", "company", "container_owner")
            .prefetch_related("crane_operations")
            .order_by("-entry_time")
        )


@extend_schema_view(
    list=extend_schema(
        tags=["Customer Pre-Orders"],
        summary="List customer pre-orders",
        description="List all pre-orders created by the authenticated customer with ordering support.",
        responses={200: CustomerPreOrderSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Customer Pre-Orders"],
        summary="Create new pre-order",
        description="Create a new pre-order for container loading/unloading. Requires plate number and operation type.",
        request=CustomerPreOrderCreateSerializer,
        responses={201: CustomerPreOrderSerializer},
    ),
    retrieve=extend_schema(
        tags=["Customer Pre-Orders"],
        summary="Get pre-order details",
        description="Retrieve detailed information about a specific pre-order owned by the customer.",
        responses={200: CustomerPreOrderSerializer},
    ),
    partial_update=extend_schema(
        tags=["Customer Pre-Orders"],
        summary="Update pre-order",
        description="Update pre-order notes. Only the 'notes' field can be modified.",
        request=CustomerPreOrderSerializer,
        responses={200: CustomerPreOrderSerializer},
    ),
    destroy=extend_schema(
        tags=["Customer Pre-Orders"],
        summary="Cancel pre-order",
        description="Cancel a pre-order. Only PENDING status orders can be cancelled.",
        responses={200: OpenApiResponse(description="Pre-order cancelled successfully")},
    ),
    pending=extend_schema(
        tags=["Customer Pre-Orders"],
        summary="Get pending pre-orders",
        description="Filter and retrieve only pre-orders with PENDING status for the authenticated customer.",
        responses={200: CustomerPreOrderSerializer(many=True)},
    ),
)
class CustomerPreOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for pre-order management (customer view).

    Customers can:
    - List their own pre-orders
    - Create new pre-orders
    - View pre-order details
    - Update notes on pre-orders
    - Cancel PENDING pre-orders
    """

    permission_classes = [IsCustomer]
    serializer_class = CustomerPreOrderSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]  # Newest first by default

    def get_queryset(self):
        """
        Get pre-orders filtered by customer.
        Customers can ONLY see their own pre-orders.
        """
        return (
            PreOrder.objects.filter(customer=self.request.user)
            .select_related("customer", "vehicle_entry")
            .order_by("-created_at")
        )

    def get_permissions(self):
        """
        Add IsCustomerOwner permission for detail views.
        """
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return [IsCustomer(), IsCustomerOwner()]
        return [IsCustomer()]

    def create(self, request, *args, **kwargs):
        """
        Create a new pre-order.
        Uses existing PreOrderService for business logic.
        """
        # Validate input
        serializer = CustomerPreOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Call existing service
        preorder_service = PreOrderService()
        try:
            preorder = preorder_service.create_preorder(
                customer=request.user,
                plate_number=serializer.validated_data["plate_number"],
                operation_type=serializer.validated_data["operation_type"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except BusinessLogicError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Return created pre-order
        response_serializer = CustomerPreOrderSerializer(preorder)
        return Response(
            {"success": True, "data": response_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        """
        Get specific pre-order details.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def partial_update(self, request, *args, **kwargs):
        """
        Update pre-order (notes only).
        """
        instance = self.get_object()

        # Only allow updating notes
        if "notes" in request.data:
            instance.notes = request.data["notes"]
            instance.save()

        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        """
        Cancel a pre-order (PENDING status only).
        Uses existing PreOrderService for business logic.
        """
        instance = self.get_object()

        # Call existing service
        preorder_service = PreOrderService()
        try:
            preorder_service.cancel_order(instance.id, request.user)
        except BusinessLogicError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"success": True, "message": "Заявка успешно отменена"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """
        Get customer's pending pre-orders only.
        """
        pending_orders = self.get_queryset().filter(status="PENDING")
        serializer = self.get_serializer(pending_orders, many=True)
        return Response({"success": True, "data": serializer.data})
