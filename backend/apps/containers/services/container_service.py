from django.db import transaction

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService

from ..models import Container


class ContainerService(BaseService):
    @transaction.atomic
    def get_or_create_container(self, container_number, iso_type="22G1"):
        """
        Get existing container or create new one.

        Args:
            container_number: Container number (4 letters + 7 digits)
            iso_type: ISO 6346 size/type code (e.g., '22G1', '42G1', '45G1')

        Returns:
            Container instance
        """
        container_number = container_number.upper()

        container, created = Container.objects.get_or_create(
            container_number=container_number, defaults={"iso_type": iso_type}
        )

        if created:
            self.logger.info(
                f"Created new container {container_number} with ISO type {iso_type}"
            )

        return container

    def find_container(self, container_number):
        """Find container by number"""
        try:
            return Container.objects.get(container_number=container_number.upper())
        except Container.DoesNotExist:
            raise BusinessLogicError(
                message=f"Контейнер {container_number} не найден",
                error_code="CONTAINER_NOT_FOUND",
            )

    def validate_container_number(self, container_number):
        """Validate container number format"""
        import re

        pattern = r"^[A-Z]{4}[0-9]{7}$"

        if not re.match(pattern, container_number.upper()):
            raise BusinessLogicError(
                message="Неверный формат номера контейнера. Ожидается: 4 буквы + 7 цифр (например: HDMU6565958)",
                error_code="INVALID_CONTAINER_FORMAT",
            )

        return container_number.upper()
