from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.containers.models import Container
from apps.core.models import TimestampedModel


class ContainerOwner(TimestampedModel):
    """
    Container owner/operator companies
    """

    name = models.CharField(
        max_length=250, unique=True, help_text="Название компании-владельца контейнера"
    )
    slug = models.SlugField(
        max_length=250, unique=True, help_text="URL-совместимый идентификатор"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Владелец контейнера"
        verbose_name_plural = "Владельцы контейнеров"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Auto-generate slug from name if not provided
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ContainerEntry(TimestampedModel):
    """
    Simple model to track containers entering the terminal
    """

    # Link to existing container
    container = models.ForeignKey(
        Container, on_delete=models.PROTECT, related_name="entries"
    )

    # Entry timestamp (auto-captured, but can be overridden for historical entries)
    entry_time = models.DateTimeField(default=timezone.now)

    # Container status
    STATUS_CHOICES = [
        ("EMPTY", "Порожний"),
        ("LADEN", "Гружёный"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    # Transport type
    TRANSPORT_CHOICES = [
        ("TRUCK", "Авто"),
        ("WAGON", "Вагон"),
        ("TRAIN", "Поезд"),
    ]
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_CHOICES)

    # Optional transport identifier (truck plate, wagon number, or train number)
    transport_number = models.CharField(
        max_length=50, blank=True, help_text="Номер авто, вагона или поезда"
    )

    # Incoming train number (if transport_type is TRAIN)
    entry_train_number = models.CharField(
        max_length=50, blank=True, default="", help_text="Номер поезда при ввозе"
    )

    # Who recorded this entry (user_type can be 'admin' or 'manager')
    recorded_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_entries",
        help_text="Пользователь (API или менеджер из Telegram), который создал запись",
    )

    # Additional information (filled later by manager)
    client_name = models.CharField(
        max_length=250, blank=True, default="", help_text="Наименование клиента"
    )
    container_owner = models.ForeignKey(
        ContainerOwner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
        help_text="Собственник контейнера",
    )
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="container_entries",
        verbose_name="Компания",
        help_text="Компания-клиент (необязательно, используйте вместо client_name)",
    )
    cargo_name = models.CharField(
        max_length=250, blank=True, default="", help_text="Наименование груза"
    )

    # Exit/removal information (filled later when container leaves terminal)
    EXIT_TRANSPORT_CHOICES = [
        ("TRUCK", "Авто"),
        ("WAGON", "Вагон"),
        ("TRAIN", "Поезд"),
    ]

    exit_date = models.DateTimeField(
        null=True, blank=True, help_text="Дата вывоза контейнера с терминала"
    )

    exit_transport_type = models.CharField(
        max_length=10,
        choices=EXIT_TRANSPORT_CHOICES,
        null=True,
        blank=True,
        help_text="Тип транспорта при вывозе",
    )

    exit_train_number = models.CharField(
        max_length=50, blank=True, default="", help_text="Номер поезда при вывозе"
    )

    exit_transport_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Номер машины/вагона при вывозе",
    )

    destination_station = models.CharField(
        max_length=250, blank=True, default="", help_text="Станция назначения"
    )

    location = models.CharField(
        max_length=250, blank=True, default="", help_text="Местоположение на терминале"
    )

    # Additional crane operation information
    additional_crane_operation_date = models.DateTimeField(
        null=True, blank=True, help_text="Дата и время дополнительной крановой операции"
    )

    note = models.TextField(blank=True, default="", help_text="Примечание")

    cargo_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Вес груза в тоннах",
    )

    class Meta:
        ordering = ["-entry_time"]
        verbose_name = "Въезд контейнера"
        verbose_name_plural = "Въезды контейнеров"
        indexes = [
            models.Index(fields=["-entry_time"], name="entry_time_idx"),
            models.Index(
                fields=["container", "-entry_time"], name="container_entry_time_idx"
            ),
            models.Index(
                fields=["status", "-entry_time"], name="status_entry_time_idx"
            ),
            models.Index(fields=["-exit_date"], name="exit_date_idx"),
            models.Index(
                fields=["exit_transport_type", "-exit_date"], name="exit_type_date_idx"
            ),
            models.Index(fields=["company"], name="company_idx"),
        ]

    @property
    def dwell_time_days(self):
        """
        Calculate dwell time in days.
        - For exited containers: days between entry and exit (minimum 1 day)
        - For containers on terminal: days between entry and today (0 is OK for same day)
        """
        if not self.entry_time:
            return None

        from django.utils import timezone

        end_date = self.exit_date if self.exit_date else timezone.now()
        delta = end_date - self.entry_time
        days = delta.days

        # For exited containers, minimum 1 day (even for same-day entry/exit)
        if self.exit_date and days == 0:
            return 1

        return days

    def get_client_display(self):
        """
        Get client name for display, preferring company name over client_name.
        Returns company.name if available, otherwise client_name.
        """
        if self.company:
            return self.company.name
        return self.client_name or ""

    def __str__(self):
        return f"{self.container.container_number} - {self.get_status_display()} - {self.entry_time}"


class CraneOperation(TimestampedModel):
    """
    Track crane operations performed on containers
    """

    container_entry = models.ForeignKey(
        ContainerEntry,
        on_delete=models.CASCADE,
        related_name="crane_operations",
        help_text="Запись въезда контейнера",
    )

    operation_date = models.DateTimeField(help_text="Дата и время крановой операции")

    class Meta:
        ordering = ["-operation_date"]
        verbose_name = "Крановая операция"
        verbose_name_plural = "Крановые операции"
        indexes = [
            models.Index(
                fields=["container_entry", "-operation_date"],
                name="crane_op_entry_date_idx",
            ),
            models.Index(fields=["-operation_date"], name="crane_op_date_idx"),
        ]

    def __str__(self):
        return f"Crane op: {self.container_entry.container.container_number} - {self.operation_date}"


class PreOrder(TimestampedModel):
    """
    Customer pre-order for container terminal operations.
    Created by customers via Telegram bot before vehicle arrival.
    Matched by plate number when security scans at gate.
    """

    # Status choices
    STATUS_CHOICES = [
        ("PENDING", "Ожидает"),
        ("MATCHED", "Сопоставлен"),
        ("COMPLETED", "Завершён"),
        ("CANCELLED", "Отменён"),
    ]

    # Operation type choices
    OPERATION_CHOICES = [
        ("LOAD", "Погрузка"),  # Ортишга
        ("UNLOAD", "Разгрузка"),  # Тушуришга
    ]

    # Customer who created this pre-order
    customer = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="pre_orders",
        limit_choices_to={"user_type": "customer"},
        help_text="Клиент, создавший заявку",
    )

    # Vehicle identification for matching at gate
    plate_number = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Номер автомобиля для сопоставления на воротах",
    )

    # Operation type: loading or unloading
    operation_type = models.CharField(
        max_length=10,
        choices=OPERATION_CHOICES,
        help_text="Тип операции (погрузка/разгрузка)",
    )

    # Truck photo uploaded during pre-order
    truck_photo = models.ForeignKey(
        "files.File",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pre_orders",
        help_text="Фото грузовика из заявки",
    )

    # Current status of the pre-order
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        help_text="Текущий статус заявки",
    )

    # Reference to vehicle entry (from vehicles app)
    vehicle_entry = models.ForeignKey(
        "vehicles.VehicleEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pre_orders",
        help_text="Запись въезда автомобиля",
    )

    # Reference to container entry when matched (optional)
    matched_entry = models.ForeignKey(
        "ContainerEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pre_orders",
        help_text="Запись въезда контейнера, созданная по этой заявке",
    )

    # Timestamp when pre-order was matched at gate
    matched_at = models.DateTimeField(
        null=True, blank=True, help_text="Время сопоставления на воротах"
    )

    # Timestamp when customer cancelled the order
    cancelled_at = models.DateTimeField(
        null=True, blank=True, help_text="Время отмены заявки клиентом"
    )

    # Optional notes from customer
    notes = models.TextField(
        blank=True, default="", help_text="Дополнительные примечания от клиента"
    )

    # Batch ID for grouping orders created together
    # When customer submits multiple plates at once, they share the same batch_id
    batch_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID группы заявок, созданных одновременно",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Предзаказ"
        verbose_name_plural = "Предзаказы"
        indexes = [
            models.Index(
                fields=["customer", "status"], name="preorder_customer_status_idx"
            ),
            models.Index(
                fields=["plate_number", "status"], name="preorder_plate_status_idx"
            ),
            models.Index(fields=["-created_at"], name="preorder_created_idx"),
            models.Index(fields=["batch_id"], name="preorder_batch_idx"),
        ]

    def __str__(self):
        return f"PreOrder {self.id}: {self.plate_number} ({self.get_operation_type_display()}) - {self.get_status_display()}"
