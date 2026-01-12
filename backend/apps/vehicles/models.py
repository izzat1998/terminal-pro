from django.db import models
from django.utils.text import slugify

from apps.core.models import TimestampedModel


class Destination(TimestampedModel):
    """
    Terminal destinations for vehicle routing with associated zones
    """

    name = models.CharField(
        max_length=200, unique=True, help_text="Название пункта назначения"
    )
    code = models.SlugField(
        max_length=50, unique=True, help_text="Уникальный код пункта назначения"
    )
    zone = models.CharField(
        max_length=10, default="", help_text="Зона на терминале (K1, K2, H1, и т.д.)"
    )
    is_active = models.BooleanField(
        default=True, help_text="Активен ли этот пункт назначения"
    )

    class Meta:
        ordering = ["zone", "name"]
        verbose_name = "Пункт назначения"
        verbose_name_plural = "Пункты назначения"

    def __str__(self):
        return f"{self.name} ({self.zone})"

    def save(self, *args, **kwargs):
        """Auto-generate code from name if not provided"""
        if not self.code:
            self.code = slugify(self.name)
        super().save(*args, **kwargs)


class VehicleEntry(TimestampedModel):
    """
    Unified model for vehicle entry/exit tracking
    Tracks both light vehicles (visitors) and cargo vehicles with detailed cargo information.
    Includes workflow status for pre-order integration.
    """

    # ===== Workflow Status =====
    STATUS_CHOICES = [
        ("WAITING", "Ожидает"),  # Customer created pre-order, vehicle not yet arrived
        ("ON_TERMINAL", "На терминале"),  # Vehicle entered terminal
        ("EXITED", "Выехал"),  # Vehicle left terminal
        ("CANCELLED", "Отменён"),  # Entry cancelled
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ON_TERMINAL",
        db_index=True,
        help_text="Текущий статус автомобиля в workflow",
    )

    # Customer who created pre-order (optional - for WAITING entries from bot)
    customer = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_vehicle_entries",
        limit_choices_to={"user_type": "customer"},
        help_text="Клиент, создавший предзаказ",
    )

    # ===== Entry Basic Information =====
    license_plate = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name="госномер",
        help_text="Государственный номер автомобиля",
    )
    entry_photos = models.ManyToManyField(
        "files.File",
        related_name="vehicle_entry_photos",
        blank=True,
        verbose_name="фото при въезде",
        help_text="Фото автомобиля при въезде (можно несколько)",
    )
    entry_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="время въезда",
        help_text="Время въезда на терминал (заполняется при check-in)",
    )
    recorded_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_vehicle_entries",
        verbose_name="зарегистрировал",
        help_text="Пользователь, зарегистрировавший въезд",
    )

    # ===== Vehicle Type Classification =====
    VEHICLE_TYPE_CHOICES = [
        ("LIGHT", "Легковой автомобиль"),
        ("CARGO", "Грузовой автомобиль"),
    ]
    vehicle_type = models.CharField(
        max_length=10,
        choices=VEHICLE_TYPE_CHOICES,
        verbose_name="тип ТС",
        help_text="Тип транспортного средства",
    )

    # ===== Light Vehicle Fields =====
    # (Only populated when vehicle_type='LIGHT')
    VISITOR_TYPE_CHOICES = [
        ("EMPLOYEE", "Сотрудник"),
        ("CLIENT", "Клиент"),
        ("GUEST", "Гость"),
    ]
    visitor_type = models.CharField(
        max_length=10,
        choices=VISITOR_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="тип посетителя",
        help_text="Тип посетителя (только для легковых автомобилей)",
    )

    # ===== Cargo Vehicle Fields =====
    # (Only populated when vehicle_type='CARGO')
    TRANSPORT_TYPE_CHOICES = [
        ("PLATFORM", "Платформа"),
        ("TRUCK", "Фура"),
        ("TRAILER", "Прицеп"),
        ("MINI_TRUCK", "Мини-грузовик"),
        ("ZIL", "ЗИЛ"),
        ("GAZELLE", "Газель"),
        ("LABO", "Лабо"),
    ]
    transport_type = models.CharField(
        max_length=15,
        choices=TRANSPORT_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="тип транспорта",
        help_text="Тип грузового транспорта",
    )

    LOAD_STATUS_CHOICES = [
        ("LOADED", "С грузом"),
        ("EMPTY", "Порожний"),
    ]
    entry_load_status = models.CharField(
        max_length=10,
        choices=LOAD_STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name="загрузка при въезде",
        help_text="Статус загрузки при въезде (только для грузовых)",
    )

    # ===== Cargo Details =====
    # (Only populated when entry_load_status='LOADED')
    CARGO_TYPE_CHOICES = [
        ("CONTAINER", "Контейнер"),
        ("FOOD", "Продукты питания"),
        ("METAL", "Металл"),
        ("WOOD", "Дерево"),
        ("CHEMICAL", "Химические вещества"),
        ("EQUIPMENT", "Оборудование"),
        ("OTHER", "Другое"),
    ]
    cargo_type = models.CharField(
        max_length=15,
        choices=CARGO_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="тип груза",
        help_text="Тип перевозимого груза",
    )

    # ===== Container-Specific Fields =====
    # (Only populated when cargo_type='CONTAINER')
    CONTAINER_SIZE_CHOICES = [
        ("1x20F", "1×20F - Один 20-футовый контейнер"),
        ("2x20F", "2×20F - Два 20-футовых контейнера"),
        ("40F", "40F - Один 40-футовый контейнер"),
    ]
    container_size = models.CharField(
        max_length=10,
        choices=CONTAINER_SIZE_CHOICES,
        null=True,
        blank=True,
        verbose_name="размер контейнера",
        help_text="Размер контейнера",
    )
    container_load_status = models.CharField(
        max_length=10,
        choices=LOAD_STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name="загрузка контейнера",
        help_text="Статус загрузки контейнера (гружёный/порожний)",
    )

    # ===== Location Assignment =====
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_entries",
        help_text="Пункт назначения (включает зону)",
    )

    # ===== Exit Information =====
    exit_photos = models.ManyToManyField(
        "files.File",
        related_name="vehicle_exit_photos",
        blank=True,
        verbose_name="фото при выезде",
        help_text="Фото автомобиля при выезде (можно несколько)",
    )
    exit_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="время выезда",
        help_text="Время выезда с терминала",
    )
    exit_load_status = models.CharField(
        max_length=10,
        choices=LOAD_STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name="загрузка при выезде",
        help_text="Статус загрузки при выезде (только для грузовых)",
    )

    # ===== Computed Properties =====
    @property
    def is_on_terminal(self):
        """Check if vehicle is currently on terminal (status-based)"""
        return self.status == "ON_TERMINAL"

    @property
    def dwell_time_hours(self):
        """Calculate time spent on terminal in hours"""
        if self.entry_time and self.exit_time:
            return round((self.exit_time - self.entry_time).total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"{self.license_plate} - {self.get_vehicle_type_display()} - {self.get_status_display()}"

    class Meta:
        ordering = ["-entry_time"]
        verbose_name = "Въезд транспорта"
        verbose_name_plural = "Въезды транспорта"
        indexes = [
            models.Index(
                fields=["license_plate", "-entry_time"], name="vehicles_plate_entry_idx"
            ),
            models.Index(fields=["-entry_time"], name="vehicles_entry_time_idx"),
            models.Index(
                fields=["vehicle_type", "-entry_time"], name="vehicles_type_entry_idx"
            ),
            models.Index(fields=["exit_time"], name="vehicles_exit_time_idx"),
            models.Index(
                fields=["destination", "-entry_time"], name="vehicles_dest_entry_idx"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["license_plate"],
                condition=models.Q(status="ON_TERMINAL"),
                name="unique_active_vehicle_plate",
                violation_error_message="Автомобиль с таким номером уже находится на терминале",
            )
        ]
