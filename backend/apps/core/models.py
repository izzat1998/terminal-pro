from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TimestampedModel(models.Model):
    """
    Abstract base model that provides created_at and updated_at timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="дата изменения")

    class Meta:
        abstract = True


class TelegramActivityLog(TimestampedModel):
    """
    Log of Telegram bot actions for auditing and analytics.
    Tracks manager and customer operations.
    """

    ACTION_CHOICES = [
        # Manager actions
        ("container_entry_created", "Контейнер добавлен"),
        ("container_exit_recorded", "Выезд контейнера"),
        ("crane_operation_added", "Крановая операция"),
        # Customer actions
        ("preorder_created", "Заявка создана"),
        ("preorder_cancelled", "Заявка отменена"),
    ]

    USER_TYPE_CHOICES = [
        ("manager", "Менеджер"),
        ("customer", "Клиент"),
    ]

    # Who performed the action
    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_activity_logs",
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    telegram_user_id = models.BigIntegerField(null=True, blank=True)

    # What action was performed
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)

    # Related object (ContainerEntry, PreOrder, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    # Flexible details storage
    details = models.JSONField(default=dict, blank=True)

    # Outcome
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Лог активности Telegram"
        verbose_name_plural = "Логи активности Telegram"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user_type", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.user} ({self.created_at:%Y-%m-%d %H:%M})"
