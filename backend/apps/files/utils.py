"""
File management utilities.
"""

from datetime import datetime
from pathlib import Path


def generate_file_path(instance, filename):
    """
    Generate organized file storage path.

    Pattern: files/{category}/{year}/{month}/{uuid}.{ext}
    Example: files/container_image/2025/10/a3d4e5f6-1234.jpg
    """
    ext = Path(filename).suffix.lower()
    category_code = (
        instance.file_category.code if instance.file_category else "uncategorized"
    )
    now = datetime.now()

    return f"files/{category_code}/{now.year}/{now.month:02d}/{instance.id}{ext}"


def get_file_dimensions(file):
    """
    Get image dimensions if file is an image.

    Returns:
        tuple: (width, height) or (None, None) if not an image
    """
    try:
        from PIL import Image

        image = Image.open(file)
        width, height = image.size
        file.seek(0)
        return width, height
    except (ImportError, Exception):
        return None, None


def format_file_size(size_bytes):
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        str: Formatted size (e.g., "2.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
