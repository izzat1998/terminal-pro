from django.contrib import admin

from .models import ContainerEntry, ContainerOwner, CraneOperation, PreOrder


class CraneOperationInline(admin.TabularInline):
    """
    Inline admin for CraneOperation - allows managing crane operations within ContainerEntry admin
    """

    model = CraneOperation
    extra = 1
    fields = ["operation_date", "created_at"]
    readonly_fields = ["created_at"]
    ordering = ["-operation_date"]


@admin.register(ContainerEntry)
class ContainerEntryAdmin(admin.ModelAdmin):
    inlines = [CraneOperationInline]
    autocomplete_fields = ["company"]

    list_display = [
        "container",
        "container_iso_type",
        "status",
        "entry_time",
        "exit_date",
        "exit_transport_type",
        "dwell_time_display",
        "recorded_by",
    ]
    list_filter = [
        "status",
        "transport_type",
        "exit_transport_type",
        "entry_time",
        "exit_date",
        "recorded_by",
        "container__iso_type",
    ]
    search_fields = [
        "container__container_number",
        "transport_number",
        "exit_train_number",
        "exit_transport_number",
        "destination_station",
        "location",
        "client_name",
        "company__name",
        "container_owner__name",
        "cargo_name",
        "note",
    ]
    readonly_fields = [
        "entry_time",
        "created_at",
        "updated_at",
        "dwell_time_days",
    ]
    ordering = ["-entry_time"]

    fieldsets = (
        (
            "Ввоз (Entry)",
            {
                "fields": (
                    "container",
                    "status",
                    "transport_type",
                    "transport_number",
                    "entry_train_number",
                    "entry_time",
                )
            },
        ),
        (
            "Бизнес-информация (Business Info)",
            {
                "fields": ("company", "client_name", "container_owner", "cargo_name"),
                "description": "Заполняется менеджером позже. Используйте 'company' для структурированных компаний.",
            },
        ),
        (
            "Вывоз (Exit)",
            {
                "fields": (
                    "exit_date",
                    "exit_transport_type",
                    "exit_train_number",
                    "exit_transport_number",
                    "destination_station",
                    "location",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Дополнительно (Additional)",
            {
                "fields": (
                    "additional_crane_operation_date",
                    "cargo_weight",
                    "dwell_time_days",
                    "note",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Системная информация",
            {
                "fields": ("recorded_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def container_iso_type(self, obj):
        return obj.container.iso_type

    container_iso_type.short_description = "ISO Type"
    container_iso_type.admin_order_field = "container__iso_type"

    def dwell_time_display(self, obj):
        """Display calculated dwell time"""
        if obj.dwell_time_days is not None:
            return f"{obj.dwell_time_days} дн."
        return "-"

    dwell_time_display.short_description = "Дней хранения"


@admin.register(ContainerOwner)
class ContainerOwnerAdmin(admin.ModelAdmin):
    """
    Admin interface for ContainerOwner model
    """

    list_display = ["name", "slug", "entries_count", "created_at", "updated_at"]
    search_fields = ["name", "slug"]
    readonly_fields = ["slug", "created_at", "updated_at"]
    ordering = ["name"]

    fieldsets = (
        ("Основная информация", {"fields": ("name", "slug")}),
        (
            "Системная информация",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def entries_count(self, obj):
        """Display count of container entries for this owner"""
        return obj.entries.count()

    entries_count.short_description = "Количество записей"


@admin.register(CraneOperation)
class CraneOperationAdmin(admin.ModelAdmin):
    """
    Admin interface for CraneOperation model
    """

    list_display = ["container_entry", "operation_date", "created_at"]
    list_filter = ["operation_date", "created_at"]
    search_fields = ["container_entry__container__container_number"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-operation_date"]

    fieldsets = (
        ("Основная информация", {"fields": ("container_entry", "operation_date")}),
        (
            "Системная информация",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(PreOrder)
class PreOrderAdmin(admin.ModelAdmin):
    """
    Admin interface for PreOrder model (customer pre-orders)
    """

    list_display = [
        "id",
        "plate_number",
        "operation_type",
        "status",
        "customer",
        "matched_entry",
        "created_at",
        "matched_at",
    ]
    list_filter = ["status", "operation_type", "created_at", "matched_at"]
    search_fields = [
        "plate_number",
        "customer__first_name",
        "customer__phone_number",
        "notes",
    ]
    readonly_fields = ["created_at", "updated_at", "matched_at", "cancelled_at"]
    ordering = ["-created_at"]
    raw_id_fields = ["customer", "matched_entry", "truck_photo"]

    fieldsets = (
        (
            "Заявка",
            {
                "fields": (
                    "customer",
                    "plate_number",
                    "operation_type",
                    "truck_photo",
                    "notes",
                )
            },
        ),
        (
            "Статус",
            {"fields": ("status", "matched_entry", "matched_at", "cancelled_at")},
        ),
        (
            "Системная информация",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
