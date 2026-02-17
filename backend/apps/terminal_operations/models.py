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

    # Telegram notification settings
    telegram_group_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Telegram группа",
        help_text="ID группы (-1001234567890) или username (@mygroup)",
    )
    telegram_group_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Название группы",
    )
    notifications_enabled = models.BooleanField(
        default=False,
        verbose_name="Уведомления включены",
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
        ("-", "-"),
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

    # IMO Hazmat Classification (International Maritime Dangerous Goods Code)
    IMO_CLASS_CHOICES = [
        ("1", "Класс 1: Взрывчатые вещества"),
        ("2", "Класс 2: Газы"),
        ("3", "Класс 3: Легковоспламеняющиеся жидкости"),
        ("4", "Класс 4: Легковоспламеняющиеся твёрдые вещества"),
        ("5", "Класс 5: Окисляющие вещества"),
        ("6", "Класс 6: Токсичные вещества"),
        ("7", "Класс 7: Радиоактивные материалы"),
        ("8", "Класс 8: Коррозионные вещества"),
        ("9", "Класс 9: Прочие опасные вещества"),
    ]
    imo_class = models.CharField(
        max_length=2,
        choices=IMO_CLASS_CHOICES,
        null=True,
        blank=True,
        help_text="Класс опасности по классификации IMO (1-9)",
    )
    is_hazmat = models.BooleanField(
        default=False,
        help_text="Контейнер содержит опасные грузы",
    )

    # Container Priority for operations
    PRIORITY_CHOICES = [
        ("NORMAL", "Обычный"),
        ("HIGH", "Высокий"),
        ("URGENT", "Срочный"),
    ]
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="NORMAL",
        help_text="Приоритет обработки контейнера",
    )

    # Shipping/Booking Information
    vessel_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Название судна",
    )
    booking_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Номер букинга/заказа",
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
        Minimum 1 day for any container - if a container is on terminal,
        it occupies space starting from day 1, not day 0.
        Also protects against negative values from timezone edge cases.
        """
        if not self.entry_time:
            return None

        from django.utils import timezone

        end_date = self.exit_date if self.exit_date else timezone.now()
        delta = end_date - self.entry_time
        days = delta.days

        # Minimum 1 day for any container (storage counts from day 1)
        # max() also protects against negative values from timezone issues
        return max(1, days)

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
        on_delete=models.SET_NULL,
        null=True,
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


class ContainerPosition(TimestampedModel):
    """
    Physical container slot in the terminal yard.
    Stores both logical grid coordinates (zone/row/bay/tier) and
    physical DXF coordinates (dxf_x/dxf_y/rotation) for 3D rendering.

    Coordinate Format: Zone-Row-Bay-Tier-Slot (e.g., A-R03-B15-T2-A)
    - Zone: A-E (5 zones)
    - Row: 1-10 (10 rows per zone)
    - Bay: 1-10 (10 bays per zone)
    - Tier: 1-4 (max 4 stacking height)
    - Sub-slot: A or B (for 20ft containers sharing a bay)

    Bay Sub-Slot Logic:
    - Each bay is sized for a 40ft container (12.2m)
    - A 40ft/45ft container occupies the full bay (uses slot 'A')
    - Two 20ft containers (6.1m each) can share a bay (slots 'A' and 'B')
    - Slot A = left/front half of bay
    - Slot B = right/back half of bay
    """

    from django.core.validators import MaxValueValidator, MinValueValidator

    # Zone choices for the terminal
    ZONE_CHOICES = [
        ("A", "Zone A"),
        ("B", "Zone B"),
        ("C", "Zone C"),
        ("D", "Zone D"),
        ("E", "Zone E"),
    ]

    # Sub-slot choices for bay subdivision (20ft containers)
    SUB_SLOT_CHOICES = [
        ("A", "Slot A (Left/Front)"),
        ("B", "Slot B (Right/Back)"),
    ]

    # Container size choices
    CONTAINER_SIZE_CHOICES = [
        ("20ft", "20ft"),
        ("40ft", "40ft"),
        ("45ft", "45ft"),
    ]

    # Occupant — nullable so empty slots can exist
    container_entry = models.OneToOneField(
        ContainerEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="position",
        help_text="Контейнер, занимающий эту позицию (null = пустой слот)",
    )

    zone = models.CharField(
        max_length=1,
        choices=ZONE_CHOICES,
        db_index=True,
        help_text="Зона терминала (A-E)",
    )

    row = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Номер ряда (1-10)",
    )

    bay = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Номер отсека (1-10)",
    )

    tier = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Ярус (1-4)",
    )

    sub_slot = models.CharField(
        max_length=1,
        choices=SUB_SLOT_CHOICES,
        default="A",
        help_text="Позиция внутри отсека: A (левая) или B (правая). 40ft контейнеры всегда занимают слот A.",
    )

    # Physical position (DXF coordinates for 3D rendering)
    dxf_x = models.FloatField(
        null=True,
        blank=True,
        help_text="Координата X из DXF-чертежа (для 3D отображения)",
    )
    dxf_y = models.FloatField(
        null=True,
        blank=True,
        help_text="Координата Y из DXF-чертежа (для 3D отображения)",
    )
    rotation = models.FloatField(
        default=0,
        help_text="Угол поворота в градусах (против часовой от оси X)",
    )
    container_size = models.CharField(
        max_length=10,
        choices=CONTAINER_SIZE_CHOICES,
        default="40ft",
        help_text="Размер контейнерного слота",
    )

    auto_assigned = models.BooleanField(
        default=False,
        help_text="Была ли позиция назначена автоматически",
    )

    class Meta:
        ordering = ["zone", "row", "bay", "tier", "sub_slot"]
        verbose_name = "Позиция контейнера"
        verbose_name_plural = "Позиции контейнеров"
        indexes = [
            models.Index(
                fields=["zone", "row", "bay", "tier", "sub_slot"],
                name="position_coords_slot_idx",
            ),
            models.Index(fields=["zone"], name="position_zone_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "row", "bay", "tier", "sub_slot"],
                name="unique_position_with_slot",
                violation_error_message="Эта позиция уже занята другим контейнером",
            )
        ]

    @property
    def coordinate_string(self) -> str:
        """Return formatted coordinate: A-R03-B15-T2-A"""
        return (
            f"{self.zone}-R{self.row:02d}-B{self.bay:02d}-T{self.tier}-{self.sub_slot}"
        )

    def __str__(self):
        return f"{self.coordinate_string} ({self.container_entry.container.container_number})"


class TerminalVehicle(TimestampedModel):
    """
    Terminal yard equipment for container handling operations.
    Used for assigning work orders to specific vehicles.
    """

    # Vehicle type choices
    TYPE_CHOICES = [
        ("REACH_STACKER", "Ричстакер"),
        ("FORKLIFT", "Погрузчик"),
        ("YARD_TRUCK", "Тягач"),
        ("RTG_CRANE", "Козловой кран (RTG)"),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Название/номер техники (например, RS-01, Погрузчик-3)",
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        help_text="Тип техники",
    )

    license_plate = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Госномер (если есть)",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Активна ли техника",
    )

    # Operator assignment (links vehicle to user via telegram_id)
    operator = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operated_vehicles",
        help_text="Оператор, работающий на этой технике",
    )

    class Meta:
        ordering = ["vehicle_type", "name"]
        verbose_name = "Техника терминала"
        verbose_name_plural = "Техника терминала"
        indexes = [
            models.Index(fields=["operator"], name="tv_operator_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_vehicle_type_display()})"


class WorkOrder(TimestampedModel):
    """
    Work order for container operations (placement or retrieval).

    Simplified workflow:
    PENDING → COMPLETED

    - PENDING: Created, container waiting for placement
    - COMPLETED: Container physically placed at target position
    """

    from django.core.validators import MaxValueValidator, MinValueValidator

    # Operation type choices
    OPERATION_CHOICES = [
        ("PLACEMENT", "Размещение"),
        ("RETRIEVAL", "Извлечение"),
    ]

    # Status workflow (simplified)
    STATUS_CHOICES = [
        ("PENDING", "Ожидает"),
        ("COMPLETED", "Завершён"),
    ]

    # Priority levels
    PRIORITY_CHOICES = [
        ("LOW", "Низкий"),
        ("MEDIUM", "Средний"),
        ("HIGH", "Высокий"),
        ("URGENT", "Срочный"),
    ]

    # Zone choices (same as ContainerPosition)
    ZONE_CHOICES = [
        ("A", "Zone A"),
        ("B", "Zone B"),
        ("C", "Zone C"),
        ("D", "Zone D"),
        ("E", "Zone E"),
    ]

    # Sub-slot choices (same as ContainerPosition)
    SUB_SLOT_CHOICES = [
        ("A", "Slot A (Left/Front)"),
        ("B", "Slot B (Right/Back)"),
    ]

    # Operation type: placement (incoming) or retrieval (outgoing)
    operation_type = models.CharField(
        max_length=10,
        choices=OPERATION_CHOICES,
        default="PLACEMENT",
        db_index=True,
        help_text="Тип операции: размещение контейнера на терминал или извлечение с терминала",
    )

    # Unique order number for display
    order_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Номер наряда (автогенерируемый)",
    )

    # Container entry to be placed or retrieved
    container_entry = models.ForeignKey(
        ContainerEntry,
        on_delete=models.PROTECT,
        related_name="work_orders",
        help_text="Контейнер для размещения или извлечения",
    )

    # Current status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        help_text="Текущий статус наряда",
    )

    # Priority
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
        db_index=True,
        help_text="Приоритет выполнения",
    )

    # Target position coordinates (where to place the container)
    target_zone = models.CharField(
        max_length=1,
        choices=ZONE_CHOICES,
        help_text="Целевая зона",
    )

    target_row = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Целевой ряд (1-20)",
    )

    target_bay = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Целевой отсек (1-10)",
    )

    target_tier = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Целевой ярус (1-4)",
    )

    target_sub_slot = models.CharField(
        max_length=1,
        choices=SUB_SLOT_CHOICES,
        default="A",
        help_text="Целевая позиция в отсеке",
    )

    # Assigned vehicle (nullable until assigned)
    assigned_to_vehicle = models.ForeignKey(
        TerminalVehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_orders",
        help_text="Техника, которой назначен наряд",
    )

    # Created by (control room operator)
    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_work_orders",
        help_text="Оператор, создавший наряд",
    )

    # Timestamp for completion
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Время завершения",
    )

    # Optional notes
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Дополнительные примечания",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Наряд на операцию"
        verbose_name_plural = "Наряды на операции"
        indexes = [
            models.Index(fields=["operation_type"], name="wo_operation_type_idx"),
            models.Index(
                fields=["status", "-created_at"], name="wo_status_created_idx"
            ),
            models.Index(
                fields=["assigned_to_vehicle", "status"], name="wo_vehicle_status_idx"
            ),
            models.Index(
                fields=["priority", "-created_at"], name="wo_priority_created_idx"
            ),
            models.Index(fields=["order_number"], name="wo_order_number_idx"),
        ]

    @property
    def target_coordinate_string(self) -> str:
        """Return formatted target coordinate: A-R03-B15-T2-A"""
        return (
            f"{self.target_zone}-R{self.target_row:02d}-B{self.target_bay:02d}-"
            f"T{self.target_tier}-{self.target_sub_slot}"
        )

    def save(self, *args, **kwargs):
        """Auto-generate order number if not set"""
        if not self.order_number:
            # Format: WO-YYYYMMDD-XXXX (e.g., WO-20260115-0001)
            from django.db.models import Max

            today = timezone.now().strftime("%Y%m%d")
            prefix = f"WO-{today}-"

            # Find max order number for today
            last_order = (
                WorkOrder.objects.filter(order_number__startswith=prefix)
                .aggregate(Max("order_number"))
                .get("order_number__max")
            )

            if last_order:
                # Extract sequence number and increment
                seq = int(last_order.split("-")[-1]) + 1
            else:
                seq = 1

            self.order_number = f"{prefix}{seq:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.order_number}: {self.container_entry.container.container_number} "
            f"→ {self.target_coordinate_string} ({self.get_status_display()})"
        )


class ContainerEvent(TimestampedModel):
    """
    Tracks all significant events in a container's lifecycle on the terminal.
    Single table design with event_type discriminator and JSON details.
    """

    EVENT_TYPE_CHOICES = [
        ("ENTRY_CREATED", "Контейнер принят"),
        ("STATUS_CHANGED", "Статус изменён"),
        ("POSITION_ASSIGNED", "Позиция назначена"),
        ("POSITION_REMOVED", "Позиция освобождена"),
        ("CRANE_OPERATION", "Крановая операция"),
        ("WORK_ORDER_CREATED", "Наряд создан"),
        ("WORK_ORDER_COMPLETED", "Наряд завершён"),
        ("EXIT_RECORDED", "Выезд зарегистрирован"),
    ]

    SOURCE_CHOICES = [
        ("API", "API"),
        ("TELEGRAM_BOT", "Telegram бот"),
        ("EXCEL_IMPORT", "Импорт Excel"),
        ("SYSTEM", "Система"),
    ]

    container_entry = models.ForeignKey(
        ContainerEntry,
        on_delete=models.CASCADE,
        related_name="events",
        help_text="Запись въезда контейнера",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        db_index=True,
        help_text="Тип события",
    )

    event_time = models.DateTimeField(
        db_index=True,
        help_text="Время события",
    )

    performed_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="container_events",
        help_text="Пользователь, выполнивший действие",
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="API",
        help_text="Источник события",
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Детали события в формате JSON",
    )

    class Meta:
        ordering = ["event_time", "created_at"]
        verbose_name = "Событие контейнера"
        verbose_name_plural = "События контейнеров"
        indexes = [
            models.Index(
                fields=["container_entry", "event_time"],
                name="event_entry_time_idx",
            ),
            models.Index(
                fields=["event_type", "-event_time"],
                name="event_type_time_idx",
            ),
            models.Index(
                fields=["-event_time"],
                name="event_time_desc_idx",
            ),
        ]

    def __str__(self):
        return f"{self.container_entry.container.container_number}: {self.get_event_type_display()} ({self.event_time})"
