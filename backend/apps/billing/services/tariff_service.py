"""
Tariff management service.

Handles creation, updating, and deletion of tariffs and their associated rates.
All business logic for tariff operations lives here; views are thin orchestration.
"""

from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import Tariff, TariffRate


class TariffService(BaseService):
    """
    Service for managing tariffs.

    Business rules:
    - Only one tariff can be active per company at any given date
    - company=NULL is the general (default) tariff
    - Tariff date ranges must not overlap for the same company
    - Deleting a tariff cascades to its rates
    """

    def create_tariff(self, data: dict, user) -> Tariff:
        """
        Create a new tariff with its associated rates.

        Args:
            data: Validated data from TariffCreateSerializer containing
                  company, effective_from, effective_to, notes, and rates.
            user: The user creating the tariff (set as created_by).

        Returns:
            The created Tariff instance.

        Raises:
            BusinessLogicError: If tariff dates overlap with an existing tariff
                                or a database constraint is violated.
        """
        rates_data = data.pop("rates")

        self._check_overlap(
            company=data.get("company"),
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
        )

        try:
            with transaction.atomic():
                tariff = Tariff.objects.create(**data, created_by=user)

                for rate_data in rates_data:
                    TariffRate.objects.create(tariff=tariff, **rate_data)
        except IntegrityError as exc:
            self.logger.error("Failed to create tariff: %s", exc)
            raise BusinessLogicError(
                "Не удалось создать тариф. Возможно, тариф с такими параметрами уже существует.",
                error_code="TARIFF_CREATE_FAILED",
            )

        self.logger.info(
            "Created tariff %d for company=%s effective_from=%s by user %s",
            tariff.id,
            tariff.company_id,
            tariff.effective_from,
            user.id,
        )
        return tariff

    def update_tariff(self, tariff_id: int, data: dict, user) -> Tariff:
        """
        Update an existing tariff (only effective_to and notes).

        Args:
            tariff_id: The ID of the tariff to update.
            data: Validated data from TariffUpdateSerializer.
            user: The user performing the update (for audit logging).

        Returns:
            The updated Tariff instance.

        Raises:
            BusinessLogicError: If the tariff is not found or update fails.
        """
        tariff = self._get_tariff(tariff_id)

        if "effective_to" in data:
            tariff.effective_to = data["effective_to"]
        if "notes" in data:
            tariff.notes = data["notes"]

        try:
            tariff.save()
        except IntegrityError as exc:
            self.logger.error("Failed to update tariff %d: %s", tariff_id, exc)
            raise BusinessLogicError(
                "Не удалось обновить тариф. Проверьте корректность данных.",
                error_code="TARIFF_UPDATE_FAILED",
            )

        self.logger.info(
            "Updated tariff %d by user %s", tariff_id, user.id
        )
        return tariff

    def delete_tariff(self, tariff_id: int, user) -> None:
        """
        Delete a tariff and its associated rates.

        Args:
            tariff_id: The ID of the tariff to delete.
            user: The user performing the deletion (for audit logging).

        Raises:
            BusinessLogicError: If the tariff is not found or cannot be deleted.
        """
        tariff = self._get_tariff(tariff_id)

        try:
            tariff.delete()
        except Exception as exc:
            self.logger.error("Failed to delete tariff %d: %s", tariff_id, exc)
            raise BusinessLogicError(
                "Не удалось удалить тариф. Возможно, он используется в других записях.",
                error_code="TARIFF_DELETE_FAILED",
            )

        self.logger.info(
            "Deleted tariff %d by user %s", tariff_id, user.id
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_tariff(self, tariff_id: int) -> Tariff:
        """Fetch a tariff by ID or raise BusinessLogicError."""
        try:
            return Tariff.objects.get(pk=tariff_id)
        except Tariff.DoesNotExist:
            raise BusinessLogicError(
                "Тариф не найден.",
                error_code="TARIFF_NOT_FOUND",
            )

    def _check_overlap(
        self,
        company,
        effective_from,
        effective_to=None,
        exclude_pk=None,
    ) -> None:
        """
        Check that the date range does not overlap with existing tariffs
        for the same company.

        Raises:
            BusinessLogicError: If an overlapping tariff exists.
        """
        overlapping = Tariff.objects.filter(
            company=company,
            effective_from__lte=effective_to or effective_from,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=effective_from)
        )

        if exclude_pk:
            overlapping = overlapping.exclude(pk=exclude_pk)

        if overlapping.exists():
            raise BusinessLogicError(
                "Даты тарифа пересекаются с существующим тарифом.",
                error_code="TARIFF_OVERLAP",
            )
