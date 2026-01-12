from django.contrib import admin

from .models import Destination, VehicleEntry


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    """
    Admin interface for Destination model
    """

    list_display = ["name", "zone", "code", "is_active", "created_at"]
    list_filter = ["is_active", "zone", "created_at"]
    search_fields = ["name", "code", "zone"]
    readonly_fields = ["code", "created_at", "updated_at"]
    ordering = ["zone", "name"]


@admin.register(VehicleEntry)
class VehicleEntryAdmin(admin.ModelAdmin):
    """
    Admin interface for VehicleEntry model
    """

    list_display = [
        "license_plate",
        "vehicle_type",
        "entry_time",
        "exit_time",
        "is_on_terminal",
        "dwell_time_hours",
        "recorded_by",
    ]
    list_filter = [
        "vehicle_type",
        "visitor_type",
        "transport_type",
        "entry_load_status",
        "cargo_type",
        "destination",
        "entry_time",
        "exit_time",
    ]
    search_fields = ["license_plate", "recorded_by__username", "recorded_by__email"]
    readonly_fields = ["is_on_terminal", "dwell_time_hours", "created_at", "updated_at"]
    date_hierarchy = "entry_time"
    ordering = ["-entry_time"]

    filter_horizontal = ["entry_photos", "exit_photos"]

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "license_plate",
                    "vehicle_type",
                    "entry_photos",
                    "entry_time",
                    "recorded_by",
                )
            },
        ),
        (
            "Легковой автомобиль",
            {"fields": ("visitor_type",), "classes": ("collapse",)},
        ),
        (
            "Грузовой автомобиль",
            {
                "fields": (
                    "transport_type",
                    "entry_load_status",
                    "cargo_type",
                    "container_size",
                    "container_load_status",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Местоположение", {"fields": ("destination",)}),
        (
            "Выезд",
            {
                "fields": ("exit_photos", "exit_time", "exit_load_status"),
                "classes": ("collapse",),
            },
        ),
        (
            "Статистика",
            {
                "fields": (
                    "is_on_terminal",
                    "dwell_time_hours",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
