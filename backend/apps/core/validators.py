"""
Custom validators for the application.
"""

from django.core.exceptions import ValidationError


def validate_image_size(file):
    """
    Validate uploaded image file size (max 10MB).
    Simple function validator - easily serializable for migrations.
    """
    max_size_mb = 10
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            f"Размер файла не может превышать {max_size_mb}МБ. "
            f"Текущий размер: {round(file.size / (1024 * 1024), 2)}МБ"
        )
