import logging

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import BusinessLogicError

from .models import CustomUser
from .serializers import (
    ManagerCreateSerializer,
    ManagerSerializer,
    ManagerStatsSerializer,
    ManagerUpdateSerializer,
)
from .services import ManagerService


logger = logging.getLogger(__name__)


class IsAdminUser(IsAuthenticated):
    """
    Permission class that checks if user is authenticated and is admin.
    Supports both CustomUser (is_admin, is_superuser) and Manager (limited to CustomUser admins).
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        # CustomUser has is_admin and is_superuser attributes
        if hasattr(request.user, "is_admin"):
            return request.user.is_admin or request.user.is_superuser

        # Manager cannot access admin endpoints
        return False


class ManagerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Telegram bot managers.
    All endpoints require admin authentication.
    """

    permission_classes = [IsAdminUser]
    service = ManagerService()

    def get_queryset(self):
        """
        Get queryset with optional filtering.
        Uses select_related to prefetch profile data for better performance.
        Filters check both profile fields and legacy fields during migration.
        """
        queryset = CustomUser.objects.filter(user_type="manager").select_related(
            "manager_profile", "manager_profile__company"
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
                Q(manager_profile__bot_access=bot_val) |
                Q(manager_profile__isnull=True, bot_access=bot_val)
            )

        # Filter by gate access (check profile first, then legacy)
        gate_access = self.request.query_params.get("gate_access")
        if gate_access is not None:
            gate_val = gate_access.lower() == "true"
            queryset = queryset.filter(
                Q(manager_profile__gate_access=gate_val) |
                Q(manager_profile__isnull=True, gate_access=gate_val)
            )

        # Filter by telegram linked status (check profile first, then legacy)
        has_telegram = self.request.query_params.get("has_telegram")
        if has_telegram is not None:
            if has_telegram.lower() == "true":
                queryset = queryset.filter(
                    Q(manager_profile__telegram_user_id__isnull=False) |
                    Q(manager_profile__isnull=True, telegram_user_id__isnull=False)
                )
            else:
                queryset = queryset.filter(
                    Q(manager_profile__telegram_user_id__isnull=True) |
                    Q(manager_profile__isnull=True, telegram_user_id__isnull=True)
                )

        # Search by name or phone (check profile first, then legacy)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(manager_profile__phone_number__icontains=search) |
                Q(manager_profile__telegram_username__icontains=search) |
                Q(manager_profile__isnull=True, phone_number__icontains=search) |
                Q(manager_profile__isnull=True, telegram_username__icontains=search)
            )

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == "create":
            return ManagerCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ManagerUpdateSerializer
        elif self.action == "stats":
            return ManagerStatsSerializer
        return ManagerSerializer

    @extend_schema(
        summary="Create manager",
        responses={
            201: ManagerSerializer,
            400: OpenApiResponse(description="Invalid data"),
            403: OpenApiResponse(description="Admin access required"),
        },
        description="Create a new manager",
    )
    def create(self, request):
        """
        Create a new manager (admin only).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            manager = self.service.create_manager(
                phone_number=serializer.validated_data["phone_number"],
                first_name=serializer.validated_data["first_name"],
                bot_access=serializer.validated_data.get("bot_access", False),
                gate_access=serializer.validated_data.get("gate_access", False),
                is_active=serializer.validated_data.get("is_active", True),
                password=serializer.validated_data.get("password"),
            )

            return Response(
                {"success": True, "data": ManagerSerializer(manager).data},
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
        summary="Update manager",
        responses={
            200: ManagerSerializer,
            400: OpenApiResponse(description="Invalid data"),
            404: OpenApiResponse(description="Manager not found"),
        },
        description="Update manager information",
    )
    def update(self, request, pk=None, partial=False):
        """
        Update manager information (admin only).
        Supports both PUT (full update) and PATCH (partial update).
        """
        manager = self.get_object()
        serializer = self.get_serializer(manager, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_manager = self.service.update_manager(
                manager_id=manager.id, **serializer.validated_data
            )

            return Response({"success": True, "data": ManagerSerializer(updated_manager).data})
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
        summary="Grant manager access",
        request=None,
        responses={
            200: ManagerSerializer,
            400: OpenApiResponse(description="Invalid request"),
            404: OpenApiResponse(description="Manager not found"),
        },
        description="Grant bot access to manager",
    )
    @action(detail=True, methods=["post"], url_path="grant-access")
    def grant_access(self, request, pk=None):
        """
        Grant bot access to a manager.
        Uses service layer to update both profile and legacy fields.
        """
        manager = self.get_object()

        try:
            updated_manager = self.service.grant_access(manager.id)
            return Response(
                {
                    "success": True,
                    "message": f"Доступ предоставлен менеджеру {updated_manager.first_name}",
                    "data": ManagerSerializer(updated_manager).data,
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
        summary="Revoke manager access",
        request=None,
        responses={
            200: ManagerSerializer,
            400: OpenApiResponse(description="Invalid request"),
            404: OpenApiResponse(description="Manager not found"),
        },
        description="Revoke bot access from manager",
    )
    @action(detail=True, methods=["post"], url_path="revoke-access")
    def revoke_access(self, request, pk=None):
        """
        Revoke bot access from a manager.
        Uses service layer to update both profile and legacy fields.
        """
        manager = self.get_object()

        try:
            updated_manager = self.service.revoke_access(manager.id)
            return Response(
                {
                    "success": True,
                    "message": f"Доступ отозван у менеджера {updated_manager.first_name}",
                    "data": ManagerSerializer(updated_manager).data,
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

    # Access requests endpoint removed - simplified workflow

    @extend_schema(
        summary="Get manager statistics",
        responses={
            200: ManagerStatsSerializer,
        },
        description="Get manager statistics",
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get statistics about managers.
        Counts from both profiles and legacy fields during migration.
        """
        total = CustomUser.objects.filter(user_type="manager").count()
        active = CustomUser.objects.filter(user_type="manager", is_active=True).count()

        # Count managers with access (profile or legacy)
        with_access = CustomUser.objects.filter(
            user_type="manager", is_active=True
        ).filter(
            Q(manager_profile__bot_access=True) |
            Q(manager_profile__isnull=True, bot_access=True)
        ).count()

        # Count managers with telegram (profile or legacy)
        with_telegram = CustomUser.objects.filter(user_type="manager").filter(
            Q(manager_profile__telegram_user_id__isnull=False) |
            Q(manager_profile__isnull=True, telegram_user_id__isnull=False)
        ).count()

        stats = {
            "total_managers": total,
            "active_managers": active,
            "managers_with_access": with_access,
            "managers_with_telegram": with_telegram,
        }

        serializer = ManagerStatsSerializer(stats)
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Delete manager",
        request=None,
        responses={
            204: OpenApiResponse(description="Manager deleted successfully"),
            404: OpenApiResponse(description="Manager not found"),
        },
        description="Delete manager permanently (hard delete)",
    )
    def destroy(self, request, pk=None):
        """
        Delete a manager permanently (hard delete).
        Removes manager record from database.
        """
        manager = self.get_object()
        manager_name = manager.full_name
        manager_id = manager.id

        # Hard delete
        manager.delete()

        logger.info(f"Deleted manager: {manager_name} (ID: {manager_id})")

        return Response(status=status.HTTP_204_NO_CONTENT)


class GateAccessCheckView(APIView):
    """
    Public endpoint for gate terminals to check user access by Telegram ID.
    No authentication required.
    """

    permission_classes = [AllowAny]
    service = ManagerService()

    @extend_schema(
        summary="Check gate access",
        parameters=[
            OpenApiParameter(
                name="telegram_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Telegram user ID to check gate access",
                required=True,
            )
        ],
        responses={
            200: OpenApiResponse(description="Access granted or denied"),
            400: OpenApiResponse(description="Missing telegram_id parameter"),
            404: OpenApiResponse(description="User not registered"),
        },
        description="Check if user has gate access by Telegram ID (public endpoint for gate terminals)",
    )
    def get(self, request):
        """
        Check gate access for a user by their Telegram ID.
        Uses service layer to find user by telegram_id (checks profiles first).

        Returns:
        - 200 with access=True if user has gate_access
        - 200 with access=False if user exists but no gate_access
        - 404 if telegram_id not found (user needs to register)
        """
        telegram_id = request.query_params.get("telegram_id")

        if not telegram_id:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_PARAMETER",
                        "message": "Параметр telegram_id обязателен",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            telegram_id = int(telegram_id)
        except ValueError:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_PARAMETER",
                        "message": "telegram_id должен быть числом",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find user by telegram_id using service (checks profiles first)
        user = self.service.get_user_by_telegram_id(telegram_id)
        if not user:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "USER_NOT_REGISTERED",
                        "message": "Пользователь не зарегистрирован. Необходимо пройти регистрацию.",
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user is active
        if not user.is_active:
            return Response(
                {
                    "success": False,
                    "access": False,
                    "error": {
                        "code": "USER_DEACTIVATED",
                        "message": "Аккаунт деактивирован",
                    },
                },
                status=status.HTTP_200_OK,
            )

        # Check gate access (from profile or legacy field)
        profile = user.get_profile()
        gate_access = profile.gate_access if profile and hasattr(profile, 'gate_access') else user.gate_access
        phone_number = profile.phone_number if profile else user.phone_number

        if gate_access:
            return Response(
                {
                    "success": True,
                    "access": True,
                    "user": {
                        "id": user.id,
                        "first_name": user.first_name,
                        "phone_number": phone_number,
                    },
                    "message": "Доступ к воротам разрешен",
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "access": False,
                    "error": {
                        "code": "NO_GATE_ACCESS",
                        "message": "Нет доступа к воротам",
                    },
                }
            )
