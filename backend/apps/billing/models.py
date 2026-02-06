from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimestampedModel


class TerminalSettings(TimestampedModel):
    """
    Singleton model for the terminal operator's own company details.

    Used in formal documents (Счёт-фактура, АКТ) as the supplier/исполнитель.
    Only one record should exist — enforced by save() override.
    """

    # Company info
    company_name = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name="Наименование организации",
        help_text='Например: ООО "MULTIMODAL TRANS TERMINAL"',
    )
    legal_address = models.TextField(
        default="",
        blank=True,
        verbose_name="Юридический адрес",
    )
    phone = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name="Телефон",
    )

    # Bank details
    bank_name = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name="Банк",
        help_text='Например: АКБ "Xamkor Bank", Яккасарой ф-л',
    )
    bank_account = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name="Расчётный счёт",
    )
    mfo = models.CharField(
        max_length=20,
        default="",
        blank=True,
        verbose_name="МФО",
    )
    inn = models.CharField(
        max_length=20,
        default="",
        blank=True,
        verbose_name="ИНН",
    )
    vat_registration_code = models.CharField(
        max_length=30,
        default="",
        blank=True,
        verbose_name="Код плательщика НДС",
    )
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("12.00"),
        verbose_name="Ставка НДС (%)",
        help_text="Текущая ставка НДС в процентах",
    )

    # Signatories
    director_name = models.CharField(
        max_length=100,
        default="",
        blank=True,
        verbose_name="Руководитель (ФИО)",
    )
    director_title = models.CharField(
        max_length=100,
        default="Руководитель",
        blank=True,
        verbose_name="Должность руководителя",
    )
    accountant_name = models.CharField(
        max_length=100,
        default="",
        blank=True,
        verbose_name="Гл. бухгалтер (ФИО)",
    )

    # Contract template
    basis_document = models.CharField(
        max_length=255,
        default="Устава",
        blank=True,
        verbose_name="Основание",
        help_text="На основании чего действует (Устава, Доверенности и т.д.)",
    )

    # Default exchange rate
    default_usd_uzs_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Курс USD → UZS",
        help_text="Курс ЦБ по умолчанию. Может быть переопределён при формировании документа.",
    )

    class Meta:
        verbose_name = "Настройки терминала"
        verbose_name_plural = "Настройки терминала"

    def __str__(self):
        return self.company_name or "Настройки терминала"

    def save(self, *args, **kwargs):
        # Enforce singleton: if another record exists, reuse its PK
        if not self.pk:
            existing = TerminalSettings.objects.first()
            if existing:
                self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "TerminalSettings":
        """Return the singleton instance, creating a blank one if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ExchangeRate(models.Model):
    """
    Cached exchange rates from the Central Bank of Uzbekistan (cbu.uz).

    Each record stores one currency rate for one date, fetched from:
      https://cbu.uz/ru/arkhiv-kursov-valyut/json/{ccy}/{date}/
    """

    currency = models.CharField(
        max_length=3,
        default="USD",
        verbose_name="Валюта",
    )
    date = models.DateField(verbose_name="Дата курса")
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Курс ЦБ",
    )
    fetched_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата загрузки",
    )

    class Meta:
        verbose_name = "Курс валюты"
        verbose_name_plural = "Курсы валют"
        constraints = [
            models.UniqueConstraint(
                fields=["currency", "date"],
                name="unique_rate_per_currency_date",
            ),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.currency} {self.date}: {self.rate}"


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


class StatementStatus(models.TextChoices):
    """Statement lifecycle statuses."""

    DRAFT = "draft", "Черновик"
    FINALIZED = "finalized", "Выставлен"
    PAID = "paid", "Оплачен"
    CANCELLED = "cancelled", "Отменён"


class StatementType(models.TextChoices):
    """Statement document types."""

    INVOICE = "invoice", "Счёт"
    CREDIT_NOTE = "credit_note", "Корректировка"


class MonthlyStatement(TimestampedModel):
    """
    Monthly billing statement for a company.

    Lifecycle: draft → finalized → paid (with optional credit notes for corrections).
    Invoice numbers are assigned only on finalization.
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

    # Document identity
    statement_type = models.CharField(
        max_length=15,
        choices=StatementType.choices,
        default=StatementType.INVOICE,
        verbose_name="Тип документа",
    )
    invoice_number = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        unique=True,
        verbose_name="Номер документа",
        help_text="Assigned on finalization, format: MTT-YYYY-NNNN or MTT-CR-YYYY-NNNN",
    )
    original_statement = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="credit_notes",
        verbose_name="Исходный документ",
        help_text="For credit notes: references the original statement being corrected",
    )

    # Lifecycle status
    status = models.CharField(
        max_length=15,
        choices=StatementStatus.choices,
        default=StatementStatus.DRAFT,
        verbose_name="Статус",
    )
    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата утверждения",
    )
    finalized_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_statements",
        verbose_name="Утвердил",
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата оплаты",
    )
    paid_marked_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_paid_statements",
        verbose_name="Отметил оплату",
    )

    # Storage totals
    total_containers = models.PositiveIntegerField(default=0, verbose_name="Всего контейнеров")
    total_billable_days = models.PositiveIntegerField(default=0, verbose_name="Оплачиваемых дней")
    total_storage_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Хранение USD"
    )
    total_storage_uzs = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="Хранение UZS"
    )

    # Services totals
    total_services_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Услуги USD"
    )
    total_services_uzs = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="Услуги UZS"
    )

    # Grand totals (storage + services)
    total_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого USD"
    )
    total_uzs = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого UZS"
    )

    # Pending containers snapshot (for exit_month billing — informational only)
    pending_containers_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Контейнеры на терминале",
        help_text="JSON snapshot of containers still on terminal at generation time",
    )

    # Exchange rate (frozen at finalization for Счёт-фактура)
    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Курс USD → UZS",
        help_text="Курс ЦБ на дату документа. Замораживается при утверждении.",
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
            # Only one invoice (non-credit-note) per company per month
            models.UniqueConstraint(
                fields=["company", "year", "month"],
                condition=models.Q(statement_type="invoice"),
                name="unique_invoice_per_company_month",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "year", "month"], name="statement_company_period_idx"),
            models.Index(fields=["year", "month"], name="statement_period_idx"),
            models.Index(fields=["status"], name="statement_status_idx"),
            models.Index(fields=["invoice_number"], name="statement_invoice_num_idx"),
        ]

    def __str__(self):
        prefix = self.invoice_number or f"DRAFT-{self.id}"
        return f"{prefix} | {self.company.name} - {self.month:02d}/{self.year}"

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

    @property
    def status_display(self) -> str:
        """Return display name for status."""
        return dict(StatementStatus.choices).get(self.status, self.status)

    @property
    def statement_type_display(self) -> str:
        """Return display name for statement type."""
        return dict(StatementType.choices).get(self.statement_type, self.statement_type)

    @property
    def is_editable(self) -> bool:
        """Only drafts can be regenerated or modified."""
        return self.status == StatementStatus.DRAFT


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

    def save(self, **kwargs):
        # Prevent modification of line items on finalized/paid statements
        # WARNING: bulk_update() bypasses this check. Use save() for individual updates.
        if self.pk and not self.statement.is_editable:
            from apps.core.exceptions import BusinessLogicError

            raise BusinessLogicError(
                "Нельзя изменить позицию утверждённого документа",
                error_code="IMMUTABLE_LINE_ITEM",
            )
        super().save(**kwargs)

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


class StatementServiceItem(TimestampedModel):
    """
    Additional charge entry within a statement.

    Stores a snapshot of an AdditionalCharge so the statement
    remains accurate even if charge data is later modified.
    """

    statement = models.ForeignKey(
        MonthlyStatement,
        on_delete=models.CASCADE,
        related_name="service_items",
        verbose_name="Выписка",
    )
    additional_charge = models.ForeignKey(
        "billing.AdditionalCharge",
        on_delete=models.SET_NULL,
        null=True,
        related_name="statement_service_items",
        verbose_name="Начисление",
    )

    # Snapshot data
    container_number = models.CharField(max_length=20, verbose_name="Номер контейнера")
    description = models.CharField(max_length=255, verbose_name="Описание услуги")
    charge_date = models.DateField(verbose_name="Дата начисления")
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма USD")
    amount_uzs = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма UZS")

    class Meta:
        verbose_name = "Позиция услуг"
        verbose_name_plural = "Позиции услуг"
        ordering = ["charge_date", "container_number"]
        indexes = [
            models.Index(fields=["statement", "charge_date"], name="svcitem_stmt_date_idx"),
        ]

    def save(self, **kwargs):
        if self.pk and not self.statement.is_editable:
            from apps.core.exceptions import BusinessLogicError

            raise BusinessLogicError(
                "Нельзя изменить позицию утверждённого документа",
                error_code="IMMUTABLE_LINE_ITEM",
            )
        super().save(**kwargs)

    def __str__(self):
        return f"{self.description} - {self.container_number} ({self.statement})"


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


class OnDemandInvoice(TimestampedModel):
    """
    On-demand invoice for specific containers.

    Created when a customer requests an immediate invoice instead of waiting
    for the monthly billing cycle. Both active and exited containers can be
    included. For active containers, costs are calculated as of today's date.

    Containers in a non-cancelled on-demand invoice are excluded from
    monthly statement generation to prevent double-billing.

    Lifecycle: draft → finalized → paid (or cancelled at any point).
    """

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="on_demand_invoices",
        verbose_name="Компания",
    )
    invoice_number = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        unique=True,
        verbose_name="Номер счёта",
        help_text="Assigned on finalization, format: OD-YYYY-NNNN",
    )
    status = models.CharField(
        max_length=15,
        choices=StatementStatus.choices,
        default=StatementStatus.DRAFT,
        verbose_name="Статус",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Примечания",
        help_text="Причина выставления разового счёта",
    )

    # Totals
    total_containers = models.PositiveIntegerField(default=0, verbose_name="Всего контейнеров")
    total_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого USD"
    )
    total_uzs = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="Итого UZS"
    )

    # Audit fields
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_on_demand_invoices",
        verbose_name="Создал",
    )
    finalized_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата утверждения"
    )
    finalized_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_on_demand_invoices",
        verbose_name="Утвердил",
    )
    paid_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата оплаты"
    )
    paid_marked_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_paid_on_demand_invoices",
        verbose_name="Отметил оплату",
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Референс платежа",
        help_text="Номер банковской транзакции, чека и т.д.",
    )
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата платежа",
        help_text="Фактическая дата оплаты (может отличаться от даты отметки)",
    )

    # Cancellation audit fields
    cancelled_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата отмены"
    )
    cancelled_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_on_demand_invoices",
        verbose_name="Отменил",
    )
    cancellation_reason = models.TextField(
        blank=True,
        default="",
        verbose_name="Причина отмены",
        help_text="Обязательно при отмене утверждённого счёта",
    )

    class Meta:
        verbose_name = "Разовый счёт"
        verbose_name_plural = "Разовые счета"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="od_invoice_company_status_idx"),
            models.Index(fields=["status"], name="od_invoice_status_idx"),
            models.Index(fields=["invoice_number"], name="od_invoice_number_idx"),
        ]

    def __str__(self):
        prefix = self.invoice_number or f"OD-DRAFT-{self.id}"
        return f"{prefix} | {self.company.name}"

    @property
    def status_display(self) -> str:
        return dict(StatementStatus.choices).get(self.status, self.status)

    @property
    def is_editable(self) -> bool:
        return self.status == StatementStatus.DRAFT


class OnDemandInvoiceItem(TimestampedModel):
    """
    Individual container cost entry within an on-demand invoice.

    Stores a snapshot of container data at generation time so the invoice
    remains accurate even if container data is later modified.
    """

    invoice = models.ForeignKey(
        OnDemandInvoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Разовый счёт",
    )
    container_entry = models.ForeignKey(
        "terminal_operations.ContainerEntry",
        on_delete=models.SET_NULL,
        null=True,
        related_name="on_demand_items",
        verbose_name="Запись контейнера",
    )

    # Snapshot data
    container_number = models.CharField(max_length=20, verbose_name="Номер контейнера")
    container_size = models.CharField(
        max_length=10, choices=ContainerSize.choices, verbose_name="Размер контейнера"
    )
    container_status = models.CharField(
        max_length=10, choices=ContainerBillingStatus.choices, verbose_name="Статус контейнера"
    )
    entry_date = models.DateField(verbose_name="Дата въезда")
    exit_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата выезда",
        help_text="NULL = контейнер на терминале при выставлении счёта",
    )

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
        verbose_name = "Позиция разового счёта"
        verbose_name_plural = "Позиции разового счёта"
        ordering = ["container_number"]
        indexes = [
            models.Index(
                fields=["invoice", "container_number"], name="od_item_invoice_container_idx"
            ),
            models.Index(fields=["container_entry"], name="od_item_entry_idx"),
        ]

    def save(self, **kwargs):
        if self.pk and not self.invoice.is_editable:
            from apps.core.exceptions import BusinessLogicError

            raise BusinessLogicError(
                "Нельзя изменить позицию утверждённого счёта",
                error_code="IMMUTABLE_LINE_ITEM",
            )
        super().save(**kwargs)

    def __str__(self):
        return f"{self.container_number} ({self.invoice})"


class OnDemandInvoiceServiceItem(TimestampedModel):
    """
    Snapshot of an additional charge included in an on-demand invoice.

    Mirrors the AdditionalCharge at generation time so the invoice
    remains accurate even if the original charge is later modified.
    """

    invoice = models.ForeignKey(
        OnDemandInvoice,
        on_delete=models.CASCADE,
        related_name="service_items",
        verbose_name="Разовый счёт",
    )
    additional_charge = models.ForeignKey(
        "billing.AdditionalCharge",
        on_delete=models.SET_NULL,
        null=True,
        related_name="on_demand_service_items",
        verbose_name="Доп. начисление",
    )

    # Snapshot data
    container_number = models.CharField(max_length=20, verbose_name="Номер контейнера")
    description = models.CharField(max_length=255, verbose_name="Описание услуги")
    charge_date = models.DateField(verbose_name="Дата начисления")
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма USD")
    amount_uzs = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма UZS")

    class Meta:
        verbose_name = "Услуга разового счёта"
        verbose_name_plural = "Услуги разового счёта"
        ordering = ["charge_date", "container_number"]
        indexes = [
            models.Index(
                fields=["invoice", "charge_date"], name="od_svc_invoice_date_idx"
            ),
        ]

    def save(self, **kwargs):
        if self.pk and not self.invoice.is_editable:
            from apps.core.exceptions import BusinessLogicError

            raise BusinessLogicError(
                "Нельзя изменить позицию утверждённого счёта",
                error_code="IMMUTABLE_LINE_ITEM",
            )
        super().save(**kwargs)

    def __str__(self):
        return f"{self.container_number}: {self.description} ({self.invoice})"
