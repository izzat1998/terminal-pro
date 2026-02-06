"""
Expense type management service.

Handles CRUD operations for expense type catalog entries.
"""

from django.db import IntegrityError

from apps.core.exceptions import BusinessLogicError
from apps.core.services.base_service import BaseService

from ..models import ExpenseType


class ExpenseTypeService(BaseService):
    """Service for managing expense types (catalog of additional charges)."""

    def create_expense_type(self, data: dict, user) -> ExpenseType:
        """
        Create a new expense type.

        Args:
            data: Validated expense type data (name, default_rate_usd, default_rate_uzs, is_active).
            user: The admin user performing the action.

        Returns:
            Created ExpenseType instance.

        Raises:
            BusinessLogicError: If an expense type with the same name already exists.
        """
        name = data.get("name", "").strip()
        if not name:
            raise BusinessLogicError(
                "Название типа расхода обязательно",
                error_code="EXPENSE_TYPE_NAME_REQUIRED",
            )

        try:
            expense_type = ExpenseType.objects.create(**data)
        except IntegrityError:
            raise BusinessLogicError(
                f"Тип расхода с названием '{name}' уже существует",
                error_code="EXPENSE_TYPE_DUPLICATE",
                details={"name": name},
            )

        self.logger.info(
            f"Expense type '{expense_type.name}' (id={expense_type.id}) created by user {user.id}"
        )
        return expense_type

    def update_expense_type(self, expense_type_id: int, data: dict, user) -> ExpenseType:
        """
        Update an existing expense type.

        Args:
            expense_type_id: ID of the expense type to update.
            data: Validated partial data to update.
            user: The admin user performing the action.

        Returns:
            Updated ExpenseType instance.

        Raises:
            BusinessLogicError: If expense type not found or name conflicts.
        """
        try:
            expense_type = ExpenseType.objects.get(pk=expense_type_id)
        except ExpenseType.DoesNotExist:
            raise BusinessLogicError(
                "Тип расхода не найден",
                error_code="EXPENSE_TYPE_NOT_FOUND",
                details={"id": expense_type_id},
            )

        # Apply updates
        for field, value in data.items():
            setattr(expense_type, field, value)

        try:
            expense_type.full_clean()
            expense_type.save()
        except IntegrityError:
            raise BusinessLogicError(
                f"Тип расхода с названием '{data.get('name', '')}' уже существует",
                error_code="EXPENSE_TYPE_DUPLICATE",
                details={"name": data.get("name", "")},
            )

        self.logger.info(
            f"Expense type '{expense_type.name}' (id={expense_type.id}) updated by user {user.id}"
        )
        return expense_type

    def delete_expense_type(self, expense_type_id: int, user) -> None:
        """
        Delete an expense type.

        Args:
            expense_type_id: ID of the expense type to delete.
            user: The admin user performing the action.

        Raises:
            BusinessLogicError: If expense type not found.
        """
        try:
            expense_type = ExpenseType.objects.get(pk=expense_type_id)
        except ExpenseType.DoesNotExist:
            raise BusinessLogicError(
                "Тип расхода не найден",
                error_code="EXPENSE_TYPE_NOT_FOUND",
                details={"id": expense_type_id},
            )

        expense_type_name = expense_type.name
        expense_type.delete()

        self.logger.info(
            f"Expense type '{expense_type_name}' (id={expense_type_id}) deleted by user {user.id}"
        )
