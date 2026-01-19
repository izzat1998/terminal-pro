from django.contrib import admin

from .models import Tariff, TariffRate


class TariffRateInline(admin.TabularInline):
    """Inline admin for TariffRate within Tariff."""

    model = TariffRate
    extra = 4  # Show 4 empty forms (one for each size/status combo)
    max_num = 4
    fields = [
        "container_size",
        "container_status",
        "daily_rate_usd",
        "daily_rate_uzs",
        "free_days",
    ]


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    """Admin configuration for Tariff model."""

    list_display = [
        "id",
        "get_tariff_type",
        "effective_from",
        "effective_to",
        "is_active",
        "created_by",
        "created_at",
    ]
    list_filter = [
        "company",
        "effective_from",
        ("effective_to", admin.EmptyFieldListFilter),
    ]
    search_fields = ["company__name", "notes"]
    date_hierarchy = "effective_from"
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["company", "created_by"]
    inlines = [TariffRateInline]

    fieldsets = [
        (
            None,
            {
                "fields": ["company", "effective_from", "effective_to"],
            },
        ),
        (
            "Информация",
            {
                "fields": ["notes", "created_by"],
            },
        ),
        (
            "Системная информация",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Тип тарифа", ordering="company")
    def get_tariff_type(self, obj):
        return obj.company.name if obj.company else "Общий"

    @admin.display(description="Активен", boolean=True)
    def is_active(self, obj):
        return obj.is_active


@admin.register(TariffRate)
class TariffRateAdmin(admin.ModelAdmin):
    """Admin configuration for TariffRate model (standalone view)."""

    list_display = [
        "id",
        "tariff",
        "container_size",
        "container_status",
        "daily_rate_usd",
        "daily_rate_uzs",
        "free_days",
    ]
    list_filter = [
        "container_size",
        "container_status",
        "tariff__company",
    ]
    search_fields = ["tariff__company__name"]
    raw_id_fields = ["tariff"]
