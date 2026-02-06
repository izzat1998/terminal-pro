"""
Additional charge service.

Handles creating, updating, and deleting one-time charges
applied to container entries (e.g., crane usage, inspection fees, penalties).
"""

from typing import TYPE_CHECKING

from django.db import transaction

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import AdditionalCharge

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser


class AdditionalChargeService(BaseService):
    """Service for managing additional charges on container entries."""

    @transaction.atomic
    def create_charge(self, data: dict, user: "CustomUser") -> AdditionalCharge:
        """
        Create a new additional charge for a container entry.

        Args:
            data: Validated charge data (container_entry, description,
                  amount_usd, amount_uzs, charge_date).
            user: The admin user creating the charge.

        Returns:
            The created AdditionalCharge instance.

        Raises:
            BusinessLogicError: If the container entry is missing.
        """
        container_entry = data.get("container_entry")
        if not container_entry:
            raise BusinessLogicError(
                "Запись контейнера обязательна",
                error_code="CONTAINER_ENTRY_REQUIRED",
            )

        charge = AdditionalCharge.objects.create(
            **data,
            created_by=user,
        )

        self.logger.info(
            "Created additional charge %d for container entry %d (USD %.2f) by user %s",
            charge.id,
            container_entry.id,
            charge.amount_usd,
            user.username,
        )
        return charge

    @transaction.atomic
    def update_charge(
        self, charge_id: int, data: dict, user: "CustomUser"
    ) -> AdditionalCharge:
        """
        Update an existing additional charge.

        Args:
            charge_id: ID of the charge to update.
            data: Validated fields to update.
            user: The admin user performing the update.

        Returns:
            The updated AdditionalCharge instance.

        Raises:
            BusinessLogicError: If the charge is not found.
        """
        try:
            charge = AdditionalCharge.objects.select_for_update().get(id=charge_id)
        except AdditionalCharge.DoesNotExist:
            raise BusinessLogicError(
                "Начисление не найдено",
                error_code="CHARGE_NOT_FOUND",
            )

        for field, value in data.items():
            setattr(charge, field, value)
        charge.save()

        self.logger.info(
            "Updated additional charge %d by user %s",
            charge.id,
            user.username,
        )
        return charge

    @transaction.atomic
    def delete_charge(self, charge_id: int, user: "CustomUser") -> None:
        """
        Delete an additional charge.

        Args:
            charge_id: ID of the charge to delete.
            user: The admin user performing the deletion.

        Raises:
            BusinessLogicError: If the charge is not found.
        """
        try:
            charge = AdditionalCharge.objects.select_for_update().get(id=charge_id)
        except AdditionalCharge.DoesNotExist:
            raise BusinessLogicError(
                "Начисление не найдено",
                error_code="CHARGE_NOT_FOUND",
            )

        charge_id_log = charge.id
        entry_id = charge.container_entry_id
        charge.delete()

        self.logger.info(
            "Deleted additional charge %d (container entry %d) by user %s",
            charge_id_log,
            entry_id,
            user.username,
        )
