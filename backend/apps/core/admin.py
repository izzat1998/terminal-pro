from django.contrib import admin

from apps.core.models import TelegramActivityLog


class TimestampedModelAdmin(admin.ModelAdmin):
    """
    Base admin class for models that inherit from TimestampedModel.
    Shows created_at and updated_at in readonly mode.
    """

    readonly_fields = ("created_at", "updated_at")

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if hasattr(self.model, "created_at"):
            list_display = list(list_display) + ["created_at", "updated_at"]
        return list_display


@admin.register(TelegramActivityLog)
class TelegramActivityLogAdmin(TimestampedModelAdmin):
    """Admin interface for viewing Telegram activity logs."""

    list_display = [
        "id",
        "action",
        "user",
        "user_type",
        "success",
        "created_at",
    ]
    list_filter = ["action", "user_type", "success", "created_at"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "details",
    ]
    readonly_fields = [
        "user",
        "user_type",
        "telegram_user_id",
        "action",
        "content_type",
        "object_id",
        "details",
        "success",
        "error_message",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
