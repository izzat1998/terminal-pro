"""
Serializers for billing models and storage cost results.
"""

from decimal import Decimal

from django.db.models import Q
from rest_framework import serializers

from apps.accounts.models import Company

from .models import AdditionalCharge, ContainerBillingStatus, ContainerSize, ExpenseType, MonthlyStatement, OnDemandInvoice, OnDemandInvoiceItem, OnDemandInvoiceServiceItem, StatementLineItem, StatementServiceItem, Tariff, TariffRate, TerminalSettings


class TerminalSettingsSerializer(serializers.ModelSerializer):
    """Serializer for the terminal operator's own company settings."""

    class Meta:
        model = TerminalSettings
        fields = [
            "id",
            "company_name",
            "legal_address",
            "phone",
            "bank_name",
            "bank_account",
            "mfo",
            "inn",
            "vat_registration_code",
            "vat_rate",
            "director_name",
            "director_title",
            "accountant_name",
            "basis_document",
            "default_usd_uzs_rate",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


def _get_user_display_name(user) -> str:
    """Return display name for a user, or empty string if None."""
    if user:
        return user.get_full_name() or user.username
    return ""


class _AuditUserNamesMixin:
    """Mixin providing display names for common audit user FKs.

    DRF only calls get_<field> for fields listed in Meta.fields,
    so serializers that don't declare a field simply ignore the extra methods.
    """

    def get_created_by_name(self, obj) -> str:
        return _get_user_display_name(obj.created_by)

    def get_finalized_by_name(self, obj) -> str:
        return _get_user_display_name(obj.finalized_by)

    def get_paid_marked_by_name(self, obj) -> str:
        return _get_user_display_name(obj.paid_marked_by)

    def get_cancelled_by_name(self, obj) -> str:
        return _get_user_display_name(getattr(obj, "cancelled_by", None))


def _get_statement_summary(obj: MonthlyStatement) -> dict:
    """Build summary dict for a statement."""
    return {
        "total_containers": obj.total_containers,
        "total_billable_days": obj.total_billable_days,
        "total_storage_usd": str(obj.total_storage_usd),
        "total_storage_uzs": str(obj.total_storage_uzs),
        "total_services_usd": str(obj.total_services_usd),
        "total_services_uzs": str(obj.total_services_uzs),
        "total_usd": str(obj.total_usd),
        "total_uzs": str(obj.total_uzs),
    }


class TariffRateSerializer(serializers.ModelSerializer):
    """Serializer for TariffRate model."""

    container_size_display = serializers.CharField(
        source="get_container_size_display", read_only=True
    )
    container_status_display = serializers.CharField(
        source="get_container_status_display", read_only=True
    )

    class Meta:
        model = TariffRate
        fields = [
            "id",
            "container_size",
            "container_size_display",
            "container_status",
            "container_status_display",
            "daily_rate_usd",
            "daily_rate_uzs",
            "free_days",
        ]
        read_only_fields = ["id"]


class TariffRateCreateSerializer(serializers.Serializer):
    """Serializer for creating TariffRate as part of Tariff creation."""

    container_size = serializers.ChoiceField(choices=ContainerSize.choices)
    container_status = serializers.ChoiceField(choices=ContainerBillingStatus.choices)
    daily_rate_usd = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    daily_rate_uzs = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    free_days = serializers.IntegerField(min_value=0, default=0)


class TariffSerializer(serializers.ModelSerializer):
    """Serializer for Tariff model (read operations)."""

    rates = TariffRateSerializer(many=True, read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    is_general = serializers.BooleanField(read_only=True)

    class Meta:
        model = Tariff
        fields = [
            "id",
            "company",
            "company_name",
            "effective_from",
            "effective_to",
            "is_active",
            "is_general",
            "notes",
            "rates",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj) -> str:
        return _get_user_display_name(obj.created_by)


class TariffCreateSerializer(serializers.Serializer):
    """Serializer for creating a new Tariff with rates."""

    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
        help_text="Company ID for special tariff, null for general tariff",
    )
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    rates = TariffRateCreateSerializer(many=True)

    def validate_rates(self, value):
        """Validate that all 4 size/status combinations are provided."""
        required_combinations = set()
        for size in ContainerSize.values:
            for status in ContainerBillingStatus.values:
                required_combinations.add((size, status))

        provided_combinations = set()
        for rate in value:
            combo = (rate["container_size"], rate["container_status"])
            if combo in provided_combinations:
                raise serializers.ValidationError(
                    f"Дублирующая ставка для {combo[0]} {combo[1]}"
                )
            provided_combinations.add(combo)

        missing = required_combinations - provided_combinations
        if missing:
            missing_str = ", ".join(f"{s} {st}" for s, st in missing)
            raise serializers.ValidationError(f"Отсутствуют ставки для: {missing_str}")

        return value

    def validate(self, attrs):
        """Validate the tariff data."""
        effective_from = attrs.get("effective_from")
        effective_to = attrs.get("effective_to")

        if effective_to and effective_to < effective_from:
            raise serializers.ValidationError(
                {"effective_to": "Дата окончания должна быть после даты начала"}
            )

        # Check for overlapping tariffs
        company = attrs.get("company")
        overlapping = Tariff.objects.filter(
            company=company,
            effective_from__lte=effective_to or effective_from,
        ).filter(
            Q(effective_to__isnull=True)
            | Q(effective_to__gte=effective_from)
        )

        # Exclude current instance if updating
        instance = self.context.get("instance")
        if instance:
            overlapping = overlapping.exclude(pk=instance.pk)

        if overlapping.exists():
            raise serializers.ValidationError(
                "Даты тарифа пересекаются с существующим тарифом"
            )

        return attrs

    def create(self, validated_data):
        """Create tariff with rates."""
        rates_data = validated_data.pop("rates")
        user = self.context["request"].user

        tariff = Tariff.objects.create(
            **validated_data,
            created_by=user,
        )

        for rate_data in rates_data:
            TariffRate.objects.create(tariff=tariff, **rate_data)

        return tariff


class TariffUpdateSerializer(serializers.Serializer):
    """Serializer for updating tariff (only effective_to and notes)."""

    effective_to = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_effective_to(self, value):
        """Validate effective_to is after effective_from."""
        instance = self.context.get("instance")
        if instance and value and value < instance.effective_from:
            raise serializers.ValidationError(
                "Дата окончания должна быть после даты начала"
            )
        return value

    def update(self, instance, validated_data):
        """Update the tariff."""
        if "effective_to" in validated_data:
            instance.effective_to = validated_data["effective_to"]
        if "notes" in validated_data:
            instance.notes = validated_data["notes"]
        instance.save()
        return instance


# Storage Cost Result Serializers


class StorageCostPeriodSerializer(serializers.Serializer):
    """Serializer for a single billing period."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days = serializers.IntegerField()
    free_days_used = serializers.IntegerField()
    billable_days = serializers.IntegerField()
    tariff_id = serializers.IntegerField()
    tariff_type = serializers.CharField()
    daily_rate_usd = serializers.DecimalField(max_digits=10, decimal_places=2)
    daily_rate_uzs = serializers.DecimalField(max_digits=15, decimal_places=2)
    amount_usd = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_uzs = serializers.DecimalField(max_digits=15, decimal_places=2)


class StorageCostResultSerializer(serializers.Serializer):
    """Serializer for complete storage cost calculation result."""

    container_entry_id = serializers.IntegerField()
    container_number = serializers.CharField()
    company_name = serializers.CharField(allow_null=True)

    # Container details
    container_size = serializers.CharField()
    container_status = serializers.CharField()

    # Dates
    entry_date = serializers.DateField()
    end_date = serializers.DateField()
    is_active = serializers.BooleanField()

    # Summary
    total_days = serializers.IntegerField()
    free_days_applied = serializers.IntegerField()
    billable_days = serializers.IntegerField()

    # Totals
    total_usd = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_uzs = serializers.DecimalField(max_digits=18, decimal_places=2)

    # Breakdown
    periods = StorageCostPeriodSerializer(many=True)

    # Metadata
    calculated_at = serializers.DateTimeField()


class BulkStorageCostRequestSerializer(serializers.Serializer):
    """Request serializer for bulk storage cost calculation."""

    container_entry_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )
    filters = serializers.DictField(required=False)
    as_of_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        """Ensure either container_entry_ids or filters is provided."""
        if not attrs.get("container_entry_ids") and not attrs.get("filters"):
            raise serializers.ValidationError("Укажите container_entry_ids или filters")
        return attrs


class BulkStorageCostSummarySerializer(serializers.Serializer):
    """Summary serializer for bulk calculation results."""

    total_containers = serializers.IntegerField()
    total_usd = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_uzs = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_billable_days = serializers.IntegerField()


class BulkStorageCostResponseSerializer(serializers.Serializer):
    """Response serializer for bulk storage cost calculation."""

    results = StorageCostResultSerializer(many=True)
    summary = BulkStorageCostSummarySerializer()


# Monthly Statement Serializers


class StatementLineItemSerializer(serializers.ModelSerializer):
    """Serializer for statement line items."""

    container_size_display = serializers.CharField(read_only=True)
    container_status_display = serializers.CharField(read_only=True)

    class Meta:
        model = StatementLineItem
        fields = [
            "id",
            "container_number",
            "container_size",
            "container_size_display",
            "container_status",
            "container_status_display",
            "period_start",
            "period_end",
            "is_still_on_terminal",
            "total_days",
            "free_days",
            "billable_days",
            "daily_rate_usd",
            "daily_rate_uzs",
            "amount_usd",
            "amount_uzs",
        ]
        read_only_fields = "__all__"


class StatementServiceItemSerializer(serializers.ModelSerializer):
    """Serializer for statement service (additional charge) items."""

    class Meta:
        model = StatementServiceItem
        fields = [
            "id",
            "container_number",
            "description",
            "charge_date",
            "amount_usd",
            "amount_uzs",
        ]
        read_only_fields = "__all__"


class MonthlyStatementListSerializer(_AuditUserNamesMixin, serializers.ModelSerializer):
    """Lightweight serializer for statement master table (no line_items)."""

    month_name = serializers.CharField(read_only=True)
    billing_method_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    statement_type_display = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    paid_marked_by_name = serializers.SerializerMethodField()
    finalized_by_name = serializers.SerializerMethodField()
    original_statement_id = serializers.IntegerField(
        source="original_statement.id", read_only=True, default=None,
    )
    summary = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyStatement
        fields = [
            "id",
            "year",
            "month",
            "month_name",
            "billing_method",
            "billing_method_display",
            "statement_type",
            "statement_type_display",
            "invoice_number",
            "original_statement_id",
            "status",
            "status_display",
            "finalized_at",
            "finalized_by_name",
            "paid_at",
            "paid_marked_by_name",
            "company_name",
            "exchange_rate",
            "summary",
            "generated_at",
        ]
        read_only_fields = "__all__"

    def get_summary(self, obj: MonthlyStatement) -> dict:
        return _get_statement_summary(obj)


class MonthlyStatementSerializer(_AuditUserNamesMixin, serializers.ModelSerializer):
    """Full serializer for monthly statements (with line_items and service_items)."""

    month_name = serializers.CharField(read_only=True)
    billing_method_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    statement_type_display = serializers.CharField(read_only=True)
    line_items = StatementLineItemSerializer(many=True, read_only=True)
    service_items = StatementServiceItemSerializer(many=True, read_only=True)
    paid_marked_by_name = serializers.SerializerMethodField()
    finalized_by_name = serializers.SerializerMethodField()
    original_statement_id = serializers.IntegerField(
        source="original_statement.id", read_only=True, default=None,
    )
    summary = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyStatement
        fields = [
            "id",
            "year",
            "month",
            "month_name",
            "billing_method",
            "billing_method_display",
            "statement_type",
            "statement_type_display",
            "invoice_number",
            "original_statement_id",
            "status",
            "status_display",
            "finalized_at",
            "finalized_by_name",
            "paid_at",
            "paid_marked_by_name",
            "summary",
            "exchange_rate",
            "line_items",
            "service_items",
            "pending_containers_data",
            "generated_at",
        ]
        read_only_fields = "__all__"

    def get_summary(self, obj: MonthlyStatement) -> dict:
        return _get_statement_summary(obj)


class AvailablePeriodSerializer(serializers.Serializer):
    """Serializer for available billing periods."""

    year = serializers.IntegerField()
    month = serializers.IntegerField()
    label = serializers.CharField()
    has_statement = serializers.BooleanField()


# Additional Charge Serializers


class AdditionalChargeSerializer(serializers.ModelSerializer):
    """Serializer for reading additional charges."""

    created_by_name = serializers.SerializerMethodField()
    container_number = serializers.CharField(
        source="container_entry.container.container_number", read_only=True
    )
    company_name = serializers.CharField(
        source="container_entry.company.name", read_only=True
    )

    class Meta:
        model = AdditionalCharge
        fields = [
            "id",
            "container_entry",
            "container_number",
            "company_name",
            "description",
            "amount_usd",
            "amount_uzs",
            "charge_date",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]

    def get_created_by_name(self, obj) -> str:
        return _get_user_display_name(obj.created_by)


class AdditionalChargeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating additional charges."""

    class Meta:
        model = AdditionalCharge
        fields = [
            "container_entry",
            "description",
            "amount_usd",
            "amount_uzs",
            "charge_date",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


# Expense Type Serializers


class ExpenseTypeSerializer(serializers.ModelSerializer):
    """Serializer for ExpenseType model."""

    class Meta:
        model = ExpenseType
        fields = [
            "id",
            "name",
            "default_rate_usd",
            "default_rate_uzs",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# On-Demand Invoice Serializers


class OnDemandInvoiceItemSerializer(serializers.ModelSerializer):
    """Serializer for on-demand invoice line items."""

    class Meta:
        model = OnDemandInvoiceItem
        fields = [
            "id",
            "container_number",
            "container_size",
            "container_status",
            "entry_date",
            "exit_date",
            "total_days",
            "free_days",
            "billable_days",
            "daily_rate_usd",
            "daily_rate_uzs",
            "amount_usd",
            "amount_uzs",
        ]
        read_only_fields = "__all__"


class OnDemandInvoiceServiceItemSerializer(serializers.ModelSerializer):
    """Serializer for on-demand invoice service (additional charge) items."""

    class Meta:
        model = OnDemandInvoiceServiceItem
        fields = [
            "id",
            "container_number",
            "description",
            "charge_date",
            "amount_usd",
            "amount_uzs",
        ]
        read_only_fields = "__all__"


class OnDemandInvoiceListSerializer(_AuditUserNamesMixin, serializers.ModelSerializer):
    """Lightweight serializer for on-demand invoice list (no items)."""

    status_display = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    pending_exit_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    finalized_by_name = serializers.SerializerMethodField()
    paid_marked_by_name = serializers.SerializerMethodField()
    cancelled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OnDemandInvoice
        fields = [
            "id",
            "invoice_number",
            "status",
            "status_display",
            "notes",
            "total_containers",
            "pending_exit_count",
            "total_usd",
            "total_uzs",
            "company_name",
            "created_by_name",
            "finalized_at",
            "finalized_by_name",
            "paid_at",
            "paid_marked_by_name",
            "payment_reference",
            "payment_date",
            "cancelled_at",
            "cancelled_by_name",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = "__all__"

    def get_pending_exit_count(self, obj: OnDemandInvoice) -> int:
        """Count items where container hasn't exited yet (still on terminal)."""
        if hasattr(obj, "_pending_exit_count"):
            return obj._pending_exit_count
        return obj.items.filter(exit_date__isnull=True).count()


class OnDemandInvoiceDetailSerializer(_AuditUserNamesMixin, serializers.ModelSerializer):
    """Full serializer for on-demand invoice with items."""

    status_display = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    items = OnDemandInvoiceItemSerializer(many=True, read_only=True)
    service_items = OnDemandInvoiceServiceItemSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    finalized_by_name = serializers.SerializerMethodField()
    paid_marked_by_name = serializers.SerializerMethodField()
    cancelled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OnDemandInvoice
        fields = [
            "id",
            "invoice_number",
            "status",
            "status_display",
            "notes",
            "total_containers",
            "total_usd",
            "total_uzs",
            "company_name",
            "items",
            "service_items",
            "created_by_name",
            "finalized_at",
            "finalized_by_name",
            "paid_at",
            "paid_marked_by_name",
            "payment_reference",
            "payment_date",
            "cancelled_at",
            "cancelled_by_name",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = "__all__"


class OnDemandInvoiceCreateSerializer(serializers.Serializer):
    """Serializer for creating an on-demand invoice."""

    container_entry_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of container entry IDs to include",
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
