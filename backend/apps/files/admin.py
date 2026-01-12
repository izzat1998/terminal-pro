from django.contrib import admin

from .models import File, FileAttachment, FileCategory


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "max_file_size_mb"]
    search_fields = ["code", "name"]


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "original_filename",
        "file_category",
        "size_mb",
        "uploaded_by",
        "created_at",
        "is_active",
    ]
    list_filter = ["file_category", "is_active", "is_public"]
    search_fields = ["original_filename"]
    readonly_fields = [
        "id",
        "size",
        "mime_type",
        "width",
        "height",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"

    def size_mb(self, obj):
        return f"{obj.size / (1024 * 1024):.2f} MB"

    size_mb.short_description = "Size"


@admin.register(FileAttachment)
class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "file",
        "content_type",
        "object_id",
        "attachment_type",
        "display_order",
    ]
    list_filter = ["content_type", "attachment_type"]
    search_fields = ["file__original_filename", "description"]
    raw_id_fields = ["file"]
