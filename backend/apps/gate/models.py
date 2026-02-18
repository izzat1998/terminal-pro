from django.db import models

from apps.core.models import TimestampedModel


class ANPRDetection(TimestampedModel):
    """
    Record of a license plate detection from the Hikvision ANPR camera.

    Each detection is stored with the raw camera data and optionally
    linked to a VehicleEntry if auto-matched.
    """

    DIRECTION_CHOICES = [
        ("approach", "Приближение"),
        ("depart", "Отъезд"),
        ("unknown", "Неизвестно"),
    ]

    plate_number = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name="номер ТС",
        help_text="Распознанный номерной знак",
    )
    confidence = models.IntegerField(
        default=0,
        verbose_name="уверенность",
        help_text="Уверенность камеры в распознавании (0-100)",
    )
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        default="unknown",
        verbose_name="направление",
    )
    vehicle_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="тип ТС",
        help_text="Тип ТС от камеры (truck, car, etc.)",
    )
    country = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="страна",
    )
    plate_color = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="цвет номера",
    )
    camera_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="время камеры",
        help_text="Время события по часам камеры",
    )
    raw_event_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="тип события",
        help_text="Тип события камеры (ANPR, etc.)",
    )
    matched_entry = models.ForeignKey(
        "vehicles.VehicleEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anpr_detections",
        verbose_name="сопоставленный въезд",
        help_text="Автоматически найденный VehicleEntry",
    )
    gate_id = models.CharField(
        max_length=50,
        default="main",
        db_index=True,
        verbose_name="ворота",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ANPR детекция"
        verbose_name_plural = "ANPR детекции"
        indexes = [
            models.Index(fields=["plate_number", "-created_at"]),
            models.Index(fields=["gate_id", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.plate_number} ({self.confidence}%) @ {self.created_at:%H:%M:%S}"
