from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimestampedModel


class ContainerSize(models.TextChoices):
    """Container size options based on ISO type first digit."""

    TWENTY_FT = "20ft", "20 футов"
    FORTY_FT = "40ft", "40 футов"


class ContainerBillingStatus(models.TextChoices):
    """Container status for billing purposes."""

    LADEN = "laden", "Груженый"
    EMPTY = "empty", "Порожний"


class Tariff(TimestampedModel):
    """
    A tariff version representing pricing rules for a time period.

    - company=NULL means this is a general (default) tariff
    - company=X means this is a special tariff for that company
    - Only one tariff can be active per company at any given date

    Business rules:
    - When a container enters, the system finds the applicable tariff
    - If company has a special tariff valid on that date, use it
    - Otherwise, fall back to general tariff (company=NULL)
    - Tariff changes mid-stay are handled by period splitting
    """

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tariffs",
        verbose_name="Компания",
        help_text="NULL = общий тариф, указана компания = специальный тариф",
    )

    effective_from = models.DateField(
        verbose_name="Действует с",
        help_text="Дата начала действия тарифа",
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
        verbose_name="Действует до",
        help_text="Дата окончания действия (NULL = действует сейчас)",
    )

    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.PROTECT,
        related_name="created_tariffs",
        verbose_name="Создан пользователем",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Примечания",
        help_text="Причина создания/изменения тарифа",
    )

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "effective_from"],
                name="unique_tariff_per_company_date",
            ),
            models.CheckConstraint(
                condition=models.Q(effective_to__isnull=True)
                | models.Q(effective_to__gte=models.F("effective_from")),
                name="tariff_effective_to_after_from",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "effective_from", "effective_to"],
                name="tariff_company_dates_idx",
            ),
            models.Index(fields=["effective_from"], name="tariff_eff_from_idx"),
            models.Index(fields=["effective_to"], name="tariff_eff_to_idx"),
        ]

    def __str__(self):
        tariff_type = self.company.name if self.company else "Общий"
        status = "активен" if self.is_active else f"до {self.effective_to}"
        return f"{tariff_type} ({self.effective_from} - {status})"

    @property
    def is_active(self) -> bool:
        """Check if this tariff is currently active."""
        from datetime import date

        today = date.today()
        # Active if: started AND (no end date OR end date is today or in the future)
        if self.effective_from > today:
            return False  # Not started yet
        if self.effective_to is None:
            return True  # No end date = ongoing
        return self.effective_to >= today  # End date hasn't passed

    @property
    def is_general(self) -> bool:
        """Check if this is a general (default) tariff."""
        return self.company is None

    def get_rate(
        self, container_size: str, container_status: str
    ) -> "TariffRate | None":
        """
        Get the rate for a specific container size and status.

        Args:
            container_size: '20ft' or '40ft'
            container_status: 'laden' or 'empty'

        Returns:
            TariffRate instance or None if not found
        """
        return self.rates.filter(
            container_size=container_size,
            container_status=container_status,
        ).first()


class TariffRate(TimestampedModel):
    """
    Pricing details for a specific container size/status combination.

    Each Tariff should have exactly 4 TariffRate records:
    - 20ft laden
    - 20ft empty
    - 40ft laden
    - 40ft empty

    Both USD and UZS rates are stored independently (not converted).
    """

    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.CASCADE,
        related_name="rates",
        verbose_name="Тариф",
    )

    container_size = models.CharField(
        max_length=10,
        choices=ContainerSize.choices,
        verbose_name="Размер контейнера",
    )

    container_status = models.CharField(
        max_length=10,
        choices=ContainerBillingStatus.choices,
        verbose_name="Статус контейнера",
    )

    daily_rate_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Ставка USD/день",
        help_text="Дневная ставка хранения в долларах США",
    )

    daily_rate_uzs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Ставка UZS/день",
        help_text="Дневная ставка хранения в сумах",
    )

    free_days = models.PositiveIntegerField(
        default=0,
        verbose_name="Бесплатные дни",
        help_text="Количество бесплатных дней хранения",
    )

    class Meta:
        verbose_name = "Ставка тарифа"
        verbose_name_plural = "Ставки тарифов"
        ordering = ["tariff", "container_size", "container_status"]
        constraints = [
            models.UniqueConstraint(
                fields=["tariff", "container_size", "container_status"],
                name="unique_rate_per_tariff_size_status",
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_container_size_display()} "
            f"{self.get_container_status_display()}: "
            f"${self.daily_rate_usd}/день"
        )


class MonthlyStatement(TimestampedModel):
    """
    Persisted monthly billing statement for a company.

    Statements are generated on-demand and cached for historical reference.
    Each statement contains line items for containers billed in that period.
    """

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="statements",
        verbose_name="Компания",
    )
    year = models.PositiveIntegerField(verbose_name="Год")
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Месяц",
    )
    billing_method = models.CharField(
        max_length=20,
        choices=[("split", "Раздельный расчёт"), ("exit_month", "По месяцу выхода")],
        verbose_name="Метод расчёта",
        help_text="Snapshot of billing method used at generation time",
    )

    # Cached totals
    total_containers = models.PositiveIntegerField(default=0, verbose_name="Всего контейнеров")
    total_billable_days = models.PositiveIntegerField(default=0, verbose_name="Оплачиваемых дней")
    total_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого USD"
    )
    total_uzs = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого UZS"
    )

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата формирования")
    generated_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_statements",
        verbose_name="Сформировано пользователем",
    )

    class Meta:
        verbose_name = "Ежемесячная выписка"
        verbose_name_plural = "Ежемесячные выписки"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "year", "month"],
                name="unique_statement_per_company_month",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "year", "month"], name="statement_company_period_idx"),
            models.Index(fields=["year", "month"], name="statement_period_idx"),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.month:02d}/{self.year}"

    @property
    def month_name(self) -> str:
        """Return Russian month name."""
        months = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
        ]
        return months[self.month - 1]

    @property
    def billing_method_display(self) -> str:
        """Return display name for billing method."""
        return "Раздельный расчёт" if self.billing_method == "split" else "По месяцу выхода"


class StatementLineItem(TimestampedModel):
    """
    Individual container cost entry within a statement.

    Stores a snapshot of container data at generation time so the statement
    remains accurate even if container data is later modified.
    """

    statement = models.ForeignKey(
        MonthlyStatement,
        on_delete=models.CASCADE,
        related_name="line_items",
        verbose_name="Выписка",
    )
    container_entry = models.ForeignKey(
        "terminal_operations.ContainerEntry",
        on_delete=models.SET_NULL,
        null=True,
        related_name="statement_line_items",
        verbose_name="Запись контейнера",
        help_text="Reference to original entry (may be null if deleted)",
    )

    # Snapshot data (won't change if container data updates)
    container_number = models.CharField(max_length=20, verbose_name="Номер контейнера")
    container_size = models.CharField(
        max_length=10,
        choices=ContainerSize.choices,
        verbose_name="Размер контейнера",
    )
    container_status = models.CharField(
        max_length=10,
        choices=ContainerBillingStatus.choices,
        verbose_name="Статус контейнера",
    )

    # Period for this statement (may be subset of total stay)
    period_start = models.DateField(verbose_name="Начало периода")
    period_end = models.DateField(verbose_name="Конец периода")
    is_still_on_terminal = models.BooleanField(default=False, verbose_name="На терминале")

    # Day breakdown
    total_days = models.PositiveIntegerField(verbose_name="Всего дней")
    free_days = models.PositiveIntegerField(verbose_name="Льготных дней")
    billable_days = models.PositiveIntegerField(verbose_name="Оплачиваемых дней")

    # Rates used
    daily_rate_usd = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Ставка USD/день"
    )
    daily_rate_uzs = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Ставка UZS/день"
    )

    # Calculated amounts
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Сумма USD")
    amount_uzs = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма UZS")

    class Meta:
        verbose_name = "Позиция выписки"
        verbose_name_plural = "Позиции выписки"
        ordering = ["container_number"]
        indexes = [
            models.Index(fields=["statement", "container_number"], name="lineitem_stmt_container_idx"),
        ]

    def __str__(self):
        return f"{self.container_number} ({self.statement})"

    @property
    def container_size_display(self) -> str:
        """Return display name for container size."""
        return "20 футов" if self.container_size == "20ft" else "40 футов"

    @property
    def container_status_display(self) -> str:
        """Return display name for container status."""
        return "Груженый" if self.container_status == "laden" else "Порожний"


class ExpenseType(TimestampedModel):
    """
    Catalog of predefined expense types for additional charges.
    Examples: Crane usage (Кран), Inspection (Досмотр), Handling, etc.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название",
    )

    default_rate_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Ставка по умолчанию (USD)",
    )

    default_rate_uzs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Ставка по умолчанию (UZS)",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
    )

    class Meta:
        verbose_name = "Тип расхода"
        verbose_name_plural = "Типы расходов"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AdditionalCharge(TimestampedModel):
    """
    Discrete one-time charge applied to a container entry.
    Examples: crane usage, inspection fee, handling charge, penalties.
    """

    container_entry = models.ForeignKey(
        "terminal_operations.ContainerEntry",
        on_delete=models.CASCADE,
        related_name="additional_charges",
        verbose_name="Запись контейнера",
    )

    description = models.CharField(
        max_length=255,
        verbose_name="Описание",
    )

    amount_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Сумма USD",
    )

    amount_uzs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Сумма UZS",
    )

    charge_date = models.DateField(
        verbose_name="Дата начисления",
    )

    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_charges",
        verbose_name="Создано пользователем",
    )

    class Meta:
        verbose_name = "Дополнительное начисление"
        verbose_name_plural = "Дополнительные начисления"
        ordering = ["-charge_date", "-created_at"]
        indexes = [
            models.Index(fields=["container_entry", "charge_date"], name="charge_entry_date_idx"),
            models.Index(fields=["charge_date"], name="charge_date_idx"),
        ]

    def __str__(self):
        return f"{self.description} - ${self.amount_usd}"
