"""
Serializers for billing models and storage cost results.
"""

from decimal import Decimal

from django.db import models
from rest_framework import serializers

from apps.accounts.models import Company

from .models import ContainerBillingStatus, ContainerSize, Tariff, TariffRate


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
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return ""


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
            models.Q(effective_to__isnull=True)
            | models.Q(effective_to__gte=effective_from)
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
