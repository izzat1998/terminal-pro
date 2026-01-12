from django.contrib import admin

from apps.core.admin import TimestampedModelAdmin

from .models import Container


@admin.register(Container)
class ContainerAdmin(TimestampedModelAdmin):
    list_display = ("container_number", "iso_type", "created_at", "updated_at")
    list_filter = ("iso_type", "created_at")
    search_fields = ("container_number",)
    ordering = ("container_number",)

    fieldsets = (
        ("Container Information", {"fields": ("container_number", "iso_type")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
