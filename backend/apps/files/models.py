"""
Centralized file management models for ERP system.
"""

import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import TimestampedModel

from .managers import FileManager
from .utils import generate_file_path


class FileCategory(models.Model):
    """
    File category definitions with validation rules.

    Examples:
    - container_image: Photos of containers
    - invoice_pdf: Invoice documents
    - bill_of_lading: Shipping documents
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Уникальный код (например, container_image)",
    )
    name = models.CharField(max_length=100, help_text="Отображаемое название")
    description = models.TextField(blank=True)

    # Validation rules
    allowed_mime_types = models.JSONField(
        default=list,
        help_text='Разрешённые MIME типы: ["image/jpeg", "application/pdf"]',
    )
    max_file_size_mb = models.IntegerField(
        default=10, help_text="Максимальный размер файла в МБ"
    )

    class Meta:
        verbose_name = "Категория файла"
        verbose_name_plural = "Категории файлов"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class File(TimestampedModel):
    """
    Centralized file storage with metadata.
    Each file is identified by UUID for security and portability.
    """

    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # File storage
    file = models.FileField(upload_to=generate_file_path, max_length=500)
    original_filename = models.CharField(
        max_length=255, help_text="Исходное имя файла при загрузке"
    )

    # Classification
    file_category = models.ForeignKey(
        FileCategory, on_delete=models.PROTECT, related_name="files"
    )

    # Metadata
    mime_type = models.CharField(max_length=100, help_text="Определённый MIME тип")
    size = models.BigIntegerField(help_text="Размер файла в байтах")

    # Ownership
    uploaded_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_files",
    )
    is_public = models.BooleanField(
        default=False, help_text="Доступен ли файл публично"
    )

    # Status
    is_active = models.BooleanField(
        default=True, db_index=True, help_text="Флаг мягкого удаления"
    )

    # Image dimensions (optional, for images only)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    # Custom manager
    objects = FileManager()

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["file_category", "-created_at"]),
            models.Index(fields=["uploaded_by", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.original_filename}"

    def is_image(self):
        """Check if file is an image."""
        return self.mime_type.startswith("image/")

    def is_document(self):
        """Check if file is a document."""
        document_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.ms-excel",
        ]
        return any(self.mime_type.startswith(doc_type) for doc_type in document_types)

    @property
    def size_mb(self):
        """Get file size in MB."""
        return round(self.size / (1024 * 1024), 2)

    @property
    def file_url(self):
        """Get file URL."""
        return self.file.url if self.file else None

    def soft_delete(self):
        """Soft delete the file."""
        self.is_active = False
        self.save(update_fields=["is_active"])

    def restore(self):
        """Restore soft-deleted file."""
        self.is_active = True
        self.save(update_fields=["is_active"])


class FileAttachment(TimestampedModel):
    """
    Generic attachment linking files to any model.

    Allows attaching files to ContainerEntry, Invoice, Purchase Order,
    or any other model using Django's ContentTypes framework.

    Example:
        # Attach image to container entry
        FileAttachment.objects.create(
            file=my_file,
            content_object=container_entry,
            attachment_type='container_photo'
        )
    """

    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="attachments")

    # Generic foreign key to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Attachment metadata
    attachment_type = models.CharField(
        max_length=50,
        help_text="Тип вложения (например, основной, дополнительный, доказательство повреждения)",
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Необязательное описание содержимого вложения",
    )
    display_order = models.IntegerField(
        default=0, help_text="Порядок отображения нескольких вложений"
    )

    class Meta:
        verbose_name = "Вложенный файл"
        verbose_name_plural = "Вложенные файлы"
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["attachment_type"]),
        ]

    def __str__(self):
        return f"{self.file.original_filename} attached to {self.content_type.model} #{self.object_id}"
