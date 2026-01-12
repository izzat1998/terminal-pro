"""
Custom managers for File model.
"""

from django.db import models


class FileManager(models.Manager):
    """Custom manager for File model with common queries."""

    def create_from_upload(self, uploaded_file, category_code, user, **kwargs):
        """
        Create File instance from uploaded file with validation.

        Args:
            uploaded_file: Django UploadedFile instance
            category_code: FileCategory code (e.g., 'container_image')
            user: User uploading the file
            **kwargs: Additional fields (is_public, etc.)

        Returns:
            File instance
        """
        from .models import FileCategory
        from .utils import get_file_dimensions
        from .validators import validate_file_category, validate_file_security

        # Get category
        try:
            category = FileCategory.objects.get(code=category_code)
        except FileCategory.DoesNotExist:
            raise ValueError(f"FileCategory '{category_code}' does not exist")

        # Security validation
        validate_file_security(uploaded_file)

        # Category validation (returns detected mime type)
        mime_type = validate_file_category(uploaded_file, category)

        # Get dimensions if image
        width, height = get_file_dimensions(uploaded_file)

        # Create file instance
        file_instance = self.create(
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_category=category,
            mime_type=mime_type,
            size=uploaded_file.size,
            uploaded_by=user,
            width=width,
            height=height,
            **kwargs,
        )

        return file_instance

    def by_category(self, category_code):
        """Filter files by category code."""
        return self.filter(file_category__code=category_code, is_active=True)

    def by_user(self, user):
        """Get files uploaded by specific user."""
        return self.filter(uploaded_by=user, is_active=True)

    def accessible_by_user(self, user):
        """
        Get files accessible to user.
        Public files + user's own files.
        """
        from django.db.models import Q

        query = Q(is_public=True) | Q(uploaded_by=user)
        return self.filter(query, is_active=True)

    def images_only(self):
        """Filter only image files."""
        return self.filter(mime_type__startswith="image/", is_active=True)

    def documents_only(self):
        """Filter document files."""
        document_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.ms-excel",
        ]
        return self.filter(mime_type__in=document_types, is_active=True)
