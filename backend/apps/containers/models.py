from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import TimestampedModel


class Container(TimestampedModel):
    """
    Container model representing shipping containers with proper validation.
    """

    # Container identification (4 letters + 7 digits)
    container_number = models.CharField(
        max_length=11,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z]{4}[0-9]{7}$",
                message="Формат: 4 буквы + 7 цифр (например, MSKU1234567)",
            )
        ],
        help_text="Номер контейнера в формате: 4 буквы + 7 цифр",
    )

    # ISO 6346 Size/Type Codes
    ISO_TYPE_CHOICES = [
        ("-", "-"),
        ("22G1", "22G1"),
        ("22K2", "22K2"),
        ("25G1", "25G1"),
        ("42G1", "42G1"),
        ("45G1", "45G1"),
        ("L5G1", "L5G1"),
        ("22R1", "22R1"),
        ("42R1", "42R1"),
        ("45R1", "45R1"),
        ("L5R1", "L5R1"),
        ("22U1", "22U1"),
        ("42U1", "42U1"),
        ("45U1", "45U1"),
        ("22P1", "22P1"),
        ("42P1", "42P1"),
        ("45P1", "45P1"),
        ("22T1", "22T1"),
        ("42T1", "42T1"),
    ]

    iso_type = models.CharField(max_length=4, choices=ISO_TYPE_CHOICES)

    class Meta:
        ordering = ["container_number"]
        verbose_name = "Контейнер"
        verbose_name_plural = "Контейнеры"

    def __str__(self):
        return f"{self.container_number} ({self.iso_type})"

    def clean(self):
        """
        Custom validation to ensure container number is uppercase.
        """
        if self.container_number:
            self.container_number = self.container_number.upper()

        super().clean()

    def save(self, *args, **kwargs):
        """
        Override save to ensure container number is always uppercase.
        """
        if self.container_number:
            self.container_number = self.container_number.upper()
        self.full_clean()
        super().save(*args, **kwargs)
