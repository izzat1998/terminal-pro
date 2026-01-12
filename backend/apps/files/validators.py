"""
File validation utilities for security and compliance.
"""

import magic
from django.core.exceptions import ValidationError


# Dangerous file extensions that should never be uploaded
DANGEROUS_EXTENSIONS = {
    "exe",
    "bat",
    "cmd",
    "com",
    "pif",
    "scr",
    "vbs",
    "js",
    "jar",
    "msi",
    "app",
    "deb",
    "rpm",
    "dmg",
    "pkg",
    "sh",
    "bash",
    "ps1",
    "psm1",
}


def validate_file_security(file):
    """
    Perform security checks on uploaded file.

    Checks for:
    - Dangerous file extensions
    - Double extensions (file.pdf.exe)
    - Path traversal attempts
    """
    filename = file.name.lower()

    # Check for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValidationError("Invalid filename: contains path traversal characters.")

    # Get all extensions (for double extension check)
    parts = filename.split(".")
    if len(parts) > 1:
        extensions = [part for part in parts[1:]]  # All parts after first dot

        # Check if any extension is dangerous
        for ext in extensions:
            if ext in DANGEROUS_EXTENSIONS:
                raise ValidationError(
                    f"File type .{ext} is not allowed for security reasons."
                )


def validate_file_category(file, category):
    """
    Validate that file matches category requirements.

    Args:
        file: UploadedFile instance
        category: FileCategory instance
    """
    # Check file size
    max_size_bytes = category.max_file_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        raise ValidationError(
            f"File size {file.size / (1024 * 1024):.2f}MB exceeds maximum "
            f"{category.max_file_size_mb}MB for {category.name}."
        )

    # Detect actual mime type using python-magic
    try:
        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)  # Reset file pointer
    except Exception:
        # Fallback to content_type from upload
        mime = file.content_type

    # Check if mime type is allowed
    allowed_types = category.allowed_mime_types
    if allowed_types and mime not in allowed_types:
        raise ValidationError(
            f"File type {mime} is not allowed for {category.name}. "
            f"Allowed types: {', '.join(allowed_types)}"
        )

    return mime


def validate_image_dimensions(file, max_width=None, max_height=None):
    """
    Validate image dimensions if limits are specified.
    """
    try:
        from PIL import Image

        image = Image.open(file)
        width, height = image.size
        file.seek(0)  # Reset file pointer

        if max_width and width > max_width:
            raise ValidationError(
                f"Image width {width}px exceeds maximum {max_width}px."
            )

        if max_height and height > max_height:
            raise ValidationError(
                f"Image height {height}px exceeds maximum {max_height}px."
            )

        return width, height
    except ImportError:
        return None, None
    except Exception as e:
        raise ValidationError(f"Invalid image file: {e!s}")
