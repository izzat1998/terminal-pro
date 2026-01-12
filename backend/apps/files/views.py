"""
API views for file management.
"""

from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.pagination import StandardResultsSetPagination

from .models import File, FileAttachment, FileCategory
from .permissions import FileAccessPermission, IsOwnerOrReadOnly
from .serializers import (
    FileAttachmentSerializer,
    FileCategorySerializer,
    FileSerializer,
    FileUploadSerializer,
)


class FileCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for file categories.
    Read-only - categories are managed by admins in Django admin.
    """

    queryset = FileCategory.objects.all()
    serializer_class = FileCategorySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "code"


class FileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for file management.

    list: Get all files accessible to user
    retrieve: Get specific file details
    create: Upload a new file
    update/partial_update: Update file metadata
    destroy: Soft delete a file
    download: Download file contents
    """

    queryset = File.objects.filter(is_active=True)
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated, FileAccessPermission]
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Filter files based on user permissions."""
        user = self.request.user

        if user.is_staff:
            # Staff sees all active files
            return File.objects.filter(is_active=True)

        # Regular users see accessible files
        return File.objects.accessible_by_user(user)

    def get_serializer_class(self):
        """Use different serializer for upload."""
        if self.action == "create":
            return FileUploadSerializer
        return FileSerializer

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        instance.soft_delete()

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """
        Download file contents.

        Returns file with proper headers for download.
        """
        file_obj = self.get_object()

        # Check permissions
        self.check_object_permissions(request, file_obj)

        # Open file for streaming
        try:
            response = FileResponse(
                file_obj.file.open("rb"), content_type=file_obj.mime_type
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{file_obj.original_filename}"'
            )
            response["Content-Length"] = file_obj.size

            # TODO: Log file access
            # FileAccessLog.objects.create(
            #     file=file_obj,
            #     user=request.user,
            #     action='download',
            #     ip_address=request.META.get('REMOTE_ADDR')
            # )

            return response
        except FileNotFoundError:
            raise Http404("File not found on storage.")

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """Restore a soft-deleted file (staff only)."""
        if not request.user.is_staff:
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Only staff can restore files."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        file_obj = File.objects.filter(id=pk).first()
        if not file_obj:
            raise Http404("File not found.")

        file_obj.restore()

        serializer = self.get_serializer(file_obj)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="my-files")
    def my_files(self, request):
        """Get files uploaded by current user."""
        files = File.objects.by_user(request.user)
        page = self.paginate_queryset(files)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(files, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="by-category")
    def by_category(self, request):
        """Filter files by category code."""
        category_code = request.query_params.get("category")

        if not category_code:
            return Response(
                {"success": False, "error": {"code": "MISSING_PARAMETER", "message": "category parameter required"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = self.get_queryset().filter(file_category__code=category_code)
        page = self.paginate_queryset(files)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(files, many=True)
        return Response({"success": True, "data": serializer.data})


class FileAttachmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for file attachments.

    Manages relationships between files and other models.
    """

    queryset = FileAttachment.objects.all()
    serializer_class = FileAttachmentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Filter attachments based on query parameters."""
        queryset = super().get_queryset()

        # Filter by content type and object id if provided
        content_type = self.request.query_params.get("content_type")
        object_id = self.request.query_params.get("object_id")

        if content_type and object_id:
            queryset = queryset.filter(
                content_type__model=content_type, object_id=object_id
            )

        return queryset
