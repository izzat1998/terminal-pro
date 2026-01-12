from django.db import transaction
from django.db.models import Q

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService

from ..models import Company


class CompanyService(BaseService):
    """
    Business logic for Company model.
    """

    def get_queryset(self, include_inactive=False):
        """
        Get base queryset for companies.

        Args:
            include_inactive: Whether to include inactive companies

        Returns:
            QuerySet of Company instances
        """
        queryset = Company.objects.all()
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset

    def search(self, query, include_inactive=False):
        """
        Search companies by name or slug.

        Args:
            query: Search string
            include_inactive: Whether to include inactive companies

        Returns:
            QuerySet of matching Company instances
        """
        queryset = self.get_queryset(include_inactive=include_inactive)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(slug__icontains=query))
        return queryset

    def get_by_id(self, company_id):
        """
        Get company by ID.

        Args:
            company_id: Company ID

        Returns:
            Company instance

        Raises:
            BusinessLogicError: If company not found
        """
        try:
            return Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise BusinessLogicError(
                message="Компания не найдена",
                error_code="COMPANY_NOT_FOUND",
                details={"company_id": company_id},
            )

    def get_by_slug(self, slug):
        """
        Get company by slug.

        Args:
            slug: Company slug

        Returns:
            Company instance

        Raises:
            BusinessLogicError: If company not found
        """
        try:
            return Company.objects.get(slug=slug)
        except Company.DoesNotExist:
            raise BusinessLogicError(
                message="Компания не найдена",
                error_code="COMPANY_NOT_FOUND",
                details={"slug": slug},
            )

    @transaction.atomic
    def create_company(self, name):
        """
        Create a new company.

        Args:
            name: Company name (required)

        Returns:
            Company instance

        Raises:
            BusinessLogicError: If company with same name already exists
        """
        # Check for duplicate name
        if Company.objects.filter(name__iexact=name.strip()).exists():
            raise BusinessLogicError(
                message=f"Компания с названием '{name}' уже существует",
                error_code="COMPANY_ALREADY_EXISTS",
                details={"name": name},
            )

        # Slug is auto-generated in model's save() method
        company = Company.objects.create(name=name.strip())

        self.logger.info(f"Created company: {company.name} (ID: {company.id}, slug: {company.slug})")
        return company

    @transaction.atomic
    def update_company(self, company_id, **kwargs):
        """
        Update company information.

        Args:
            company_id: Company ID to update
            **kwargs: Fields to update (name, is_active, telegram_group_id,
                      telegram_group_name, notifications_enabled)

        Returns:
            Updated Company instance

        Raises:
            BusinessLogicError: If company not found or name already taken
        """
        company = self.get_by_id(company_id)

        # Check for duplicate name if name is being changed
        if "name" in kwargs:
            new_name = kwargs["name"].strip()
            if Company.objects.filter(name__iexact=new_name).exclude(id=company_id).exists():
                raise BusinessLogicError(
                    message=f"Компания с названием '{new_name}' уже существует",
                    error_code="COMPANY_NAME_EXISTS",
                    details={"name": new_name},
                )
            company.name = new_name
            # Regenerate slug when name changes
            company.slug = ""  # Reset slug to trigger auto-generation

        if "is_active" in kwargs:
            company.is_active = kwargs["is_active"]

        # Handle Telegram notification settings
        if "telegram_group_id" in kwargs:
            company.telegram_group_id = kwargs["telegram_group_id"]

        if "telegram_group_name" in kwargs:
            company.telegram_group_name = kwargs["telegram_group_name"]

        if "notifications_enabled" in kwargs:
            company.notifications_enabled = kwargs["notifications_enabled"]

        company.save()

        self.logger.info(f"Updated company {company.name}: {list(kwargs.keys())}")
        return company

    @transaction.atomic
    def delete_company(self, company_id, hard_delete=False):
        """
        Delete a company.

        Args:
            company_id: Company ID to delete
            hard_delete: If True, permanently delete. If False, soft delete (set is_active=False)

        Returns:
            dict with deletion info

        Raises:
            BusinessLogicError: If company not found
        """
        company = self.get_by_id(company_id)
        company_name = company.name

        if hard_delete:
            company.delete()
            self.logger.info(f"Hard deleted company: {company_name} (ID: {company_id})")
            return {"deleted": True, "hard_delete": True, "name": company_name}
        else:
            company.is_active = False
            company.save()
            self.logger.info(f"Soft deleted company: {company_name} (ID: {company_id})")
            return {"deleted": True, "hard_delete": False, "name": company_name}
