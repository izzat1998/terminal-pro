"""
Serializers for file management API.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import File, FileAttachment, FileCategory


class FileCategorySerializer(serializers.ModelSerializer):
    """Serializer for file categories."""

    class Meta:
        model = FileCategory
        fields = [
            "id",
            "code",
            "name",
            "description",
            "allowed_mime_types",
            "max_file_size_mb",
        ]
        read_only_fields = ["id"]


class FileSerializer(serializers.ModelSerializer):
    """Serializer for file information."""

    file_url = serializers.SerializerMethodField()
    size_mb = serializers.ReadOnlyField()
    category_name = serializers.CharField(source="file_category.name", read_only=True)
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True
    )

    class Meta:
        model = File
        fields = [
            "id",
            "file_url",
            "original_filename",
            "file_category",
            "category_name",
            "mime_type",
            "size",
            "size_mb",
            "uploaded_by",
            "uploaded_by_username",
            "is_public",
            "is_active",
            "width",
            "height",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "size",
            "mime_type",
            "width",
            "height",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field({"type": "string", "format": "uri", "nullable": True})
    def get_file_url(self, obj):
        """Get absolute file URL."""
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file_url


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload."""

    file = serializers.FileField()
    category = serializers.CharField(
        help_text="File category code (e.g., container_image)"
    )
    description = serializers.CharField(required=False, allow_blank=True)
    is_public = serializers.BooleanField(default=False)

    def validate_category(self, value):
        """Validate category exists."""
        try:
            FileCategory.objects.get(code=value)
            return value
        except FileCategory.DoesNotExist:
            raise serializers.ValidationError(
                f"Категория файла '{value}' не существует."
            )

    def create(self, validated_data):
        """Create file using FileManager."""
        uploaded_file = validated_data.pop("file")
        category_code = validated_data.pop("category")
        validated_data.pop("description", None)  # Remove description, not a File field
        user = self.context["request"].user

        file_instance = File.objects.create_from_upload(
            uploaded_file=uploaded_file,
            category_code=category_code,
            user=user,
            **validated_data,
        )

        return file_instance


class FileAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for file attachments."""

    file_detail = FileSerializer(source="file", read_only=True)

    class Meta:
        model = FileAttachment
        fields = [
            "id",
            "file",
            "file_detail",
            "attachment_type",
            "description",
            "display_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AttachFileSerializer(serializers.Serializer):
    """Serializer for attaching existing file to a model."""

    file_id = serializers.UUIDField()
    attachment_type = serializers.CharField(max_length=50)
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )
    display_order = serializers.IntegerField(default=0)

    def validate_file_id(self, value):
        """Validate file exists and is active."""
        try:
            file = File.objects.get(id=value, is_active=True)
            return file
        except File.DoesNotExist:
            raise serializers.ValidationError("Файл не найден или неактивен.")
