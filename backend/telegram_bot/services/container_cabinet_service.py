"""
Service for customer container cabinet - fetching company containers.
"""

import logging
import math
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from apps.accounts.models import CustomUser
from apps.files.models import FileAttachment
from apps.terminal_operations.models import ContainerEntry


logger = logging.getLogger(__name__)


@dataclass
class PaginatedContainers:
    """Result of paginated container query"""

    containers: list[ContainerEntry]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class ContainerCabinetService:
    """Service for customer container cabinet operations"""

    def __init__(self, page_size: int = 5):
        self.page_size = page_size

    def get_customer_company(self, customer: "CustomUser"):
        """Get company from customer profile or legacy field"""
        return customer.profile_company

    def _get_company_customer_ids(self, company) -> list[int]:
        """Get all customer IDs belonging to a company"""
        return list(
            CustomUser.objects.filter(user_type="customer")
            .filter(
                Q(customer_profile__company=company)
                | Q(customer_profile__isnull=True, company=company)
            )
            .values_list("id", flat=True)
        )

    def _get_company_containers_queryset(self, company):
        """
        Get queryset of containers for a company.

        Containers are included if EITHER:
        1. Entry has a PreOrder from a customer belonging to this company, OR
        2. Entry's company field directly matches this company
        """
        customer_ids = self._get_company_customer_ids(company)

        return (
            ContainerEntry.objects.filter(
                Q(pre_orders__customer_id__in=customer_ids) | Q(company=company)
            )
            .select_related("container", "container_owner", "company")
            .prefetch_related("crane_operations")
            .distinct()
        )

    def get_active_containers(
        self, customer: "CustomUser", page: int = 1
    ) -> PaginatedContainers:
        """
        Get active containers (on terminal) for customer's company.

        Args:
            customer: The customer user
            page: Page number (1-indexed)

        Returns:
            PaginatedContainers with containers and pagination info
        """
        company = self.get_customer_company(customer)

        if not company:
            return PaginatedContainers(
                containers=[],
                total_count=0,
                page=1,
                page_size=self.page_size,
                total_pages=0,
            )

        # Get active containers (not exited)
        queryset = self._get_company_containers_queryset(company).filter(
            exit_date__isnull=True
        )

        # Order by entry time descending (newest first)
        queryset = queryset.order_by("-entry_time")

        # Get total count
        total_count = queryset.count()
        total_pages = max(1, math.ceil(total_count / self.page_size))

        # Clamp page to valid range
        page = max(1, min(page, total_pages))

        # Calculate offset
        offset = (page - 1) * self.page_size

        # Get page of containers
        containers = list(queryset[offset : offset + self.page_size])

        return PaginatedContainers(
            containers=containers,
            total_count=total_count,
            page=page,
            page_size=self.page_size,
            total_pages=total_pages,
        )

    def search_container(
        self, customer: "CustomUser", container_number: str
    ) -> ContainerEntry | None:
        """
        Search for a container by number within customer's company scope.

        Args:
            customer: The customer user
            container_number: Container number to search for (partial match)

        Returns:
            ContainerEntry if found, None otherwise
        """
        company = self.get_customer_company(customer)

        if not company:
            return None

        # Normalize search query
        container_number = container_number.upper().strip()

        # Get company containers and filter by container number
        queryset = self._get_company_containers_queryset(company).filter(
            container__container_number__icontains=container_number,
            exit_date__isnull=True,  # Only active containers
        )

        return queryset.first()

    def get_container_by_id(
        self, customer: "CustomUser", entry_id: int
    ) -> ContainerEntry | None:
        """
        Get container entry by ID, validating it belongs to customer's company.

        Args:
            customer: The customer user
            entry_id: ContainerEntry ID

        Returns:
            ContainerEntry if found and accessible, None otherwise
        """
        company = self.get_customer_company(customer)

        if not company:
            return None

        queryset = self._get_company_containers_queryset(company).filter(id=entry_id)

        return queryset.first()

    def get_container_photos(self, entry_id: int) -> list[FileAttachment]:
        """
        Get photos attached to a container entry.

        Args:
            entry_id: ContainerEntry ID

        Returns:
            List of FileAttachment objects with photos
        """
        content_type = ContentType.objects.get_for_model(ContainerEntry)

        attachments = (
            FileAttachment.objects.filter(
                content_type=content_type,
                object_id=entry_id,
                file__is_active=True,
            )
            .select_related("file")
            .order_by("display_order", "created_at")
        )

        # Filter to only valid files that exist
        valid_photos = []
        for attachment in attachments:
            if attachment.file and attachment.file.file:
                valid_photos.append(attachment)

        return valid_photos[:10]  # Telegram limit: 10 photos per album

    def get_photo_count(self, entry_id: int) -> int:
        """Get count of photos for a container entry"""
        content_type = ContentType.objects.get_for_model(ContainerEntry)

        return FileAttachment.objects.filter(
            content_type=content_type,
            object_id=entry_id,
            file__is_active=True,
        ).count()
