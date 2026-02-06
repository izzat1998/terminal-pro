"""
Permissions for file access control.
"""

from rest_framework import permissions


class FileAccessPermission(permissions.BasePermission):
    """
    Permission check for file access:
    - Public files: anyone can view
    - Private files: only owner and staff
    """

    def has_permission(self, request, view):
        """Check if user can access files endpoint."""
        # Authenticated users can upload files
        if request.method == "POST":
            return request.user and request.user.is_authenticated

        # Anyone can list/view (object-level permissions will filter)
        return True

    def has_object_permission(self, request, view, obj):
        """Check if user can access specific file."""
        # Public files - anyone can view
        if obj.is_public and request.method in permissions.SAFE_METHODS:
            return True

        # Owner has full access
        if obj.uploaded_by == request.user:
            return True

        # Staff/admin has full access
        if request.user and request.user.is_staff:
            return True

        # Deny by default
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit/delete.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner or staff
        owner = getattr(obj, "uploaded_by", None)
        if owner is None and hasattr(obj, "file"):
            owner = getattr(obj.file, "uploaded_by", None)
        return owner == request.user or request.user.is_staff
