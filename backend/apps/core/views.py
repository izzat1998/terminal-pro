from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import TelegramActivityLog
from apps.core.pagination import StandardResultsSetPagination
from apps.core.serializers import (
    TelegramActivityLogSerializer,
    TelegramActivityLogSummarySerializer,
)
from apps.core.services.telegram_group_test_service import TelegramGroupTestService


class TelegramActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Telegram bot activity logs.
    Read-only - logs are created automatically by the bot.

    Supports filtering by:
    - action: Filter by action type (e.g., container_entry_created)
    - user_type: Filter by user type (manager/customer)
    - success: Filter by success status (true/false)
    - user: Filter by user ID

    Supports search on:
    - User's full name, username
    - Details JSON field

    Supports ordering by:
    - created_at (default: -created_at)
    - action
    - user_type
    """

    queryset = TelegramActivityLog.objects.select_related("user").all()
    serializer_class = TelegramActivityLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["action", "user_type", "success", "user"]
    search_fields = [
        "user__first_name",
        "user__last_name",
        "user__username",
        "details",
    ]
    ordering_fields = ["created_at", "action", "user_type"]
    ordering = ["-created_at"]

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Get summary statistics for activity logs.

        Query params:
        - days: Number of days to look back (default: 7)

        Returns:
        - total_count: Total number of activities
        - success_count: Number of successful activities
        - error_count: Number of failed activities
        - by_action: Breakdown by action type
        - by_user_type: Breakdown by user type
        """

        days = int(request.query_params.get("days", 7))
        since = timezone.now() - timedelta(days=days)

        queryset = self.get_queryset().filter(created_at__gte=since)

        # Get counts
        total_count = queryset.count()
        success_count = queryset.filter(success=True).count()
        error_count = queryset.filter(success=False).count()

        # Get breakdown by action
        by_action_qs = (
            queryset.values("action").annotate(count=Count("id")).order_by("-count")
        )

        # Map action codes to display names
        action_choices = dict(TelegramActivityLog.ACTION_CHOICES)
        by_action = [
            {
                "action": item["action"],
                "action_display": action_choices.get(item["action"], item["action"]),
                "count": item["count"],
            }
            for item in by_action_qs
        ]

        # Get breakdown by user type
        by_user_type_qs = (
            queryset.values("user_type").annotate(count=Count("id")).order_by("-count")
        )
        by_user_type = {item["user_type"]: item["count"] for item in by_user_type_qs}

        data = {
            "total_count": total_count,
            "success_count": success_count,
            "error_count": error_count,
            "by_action": by_action,
            "by_user_type": by_user_type,
        }

        serializer = TelegramActivityLogSummarySerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="recent")
    def recent(self, request):
        """
        Get recent activity logs (last 24 hours) without pagination.
        Limited to 50 most recent entries.
        """

        since = timezone.now() - timedelta(hours=24)
        queryset = self.get_queryset().filter(created_at__gte=since)[:50]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TestTelegramGroupView(APIView):
    """
    Test if the Telegram bot has access to a group.

    POST /api/telegram/test-group/
    {
        "group_id": "-1001234567890"  // or "@groupname"
    }

    Returns group info on success, error details on failure.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        group_id = request.data.get("group_id", "").strip()

        if not group_id:
            return Response(
                {
                    "success": False,
                    "data": {
                        "accessible": False,
                        "error_code": "INVALID_ID",
                        "error_message": "ID группы не указан",
                    },
                },
                status=400,
            )

        service = TelegramGroupTestService()
        result = service.test_group(group_id)

        if result.accessible:
            return Response(
                {
                    "success": True,
                    "data": {
                        "accessible": True,
                        "group_title": result.group_title,
                        "group_type": result.group_type,
                        "member_count": result.member_count,
                    },
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "data": {
                        "accessible": False,
                        "error_code": result.error_code,
                        "error_message": result.error_message,
                    },
                }
            )
