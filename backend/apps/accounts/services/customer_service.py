from django.db import models, transaction

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService

from ..models import Company, CustomerProfile, CustomUser, ManagerProfile
from .manager_service import ManagerService


class CustomerService(BaseService):
    """
    Business logic for Customer users and their Telegram bot access.

    NOTE: This service is being migrated to use CustomerProfile instead of
    legacy fields on CustomUser. During migration, it writes to both
    CustomerProfile AND legacy CustomUser fields for backward compatibility.
    """

    def __init__(self):
        super().__init__()
        # Reuse phone validation from ManagerService
        self._manager_service = ManagerService()

    def validate_phone_number(self, phone_number):
        """
        Validate phone number format.
        Delegates to ManagerService for consistency.

        Args:
            phone_number: Phone number string to validate

        Returns:
            Cleaned phone number

        Raises:
            BusinessLogicError: If phone number format is invalid
        """
        return self._manager_service.validate_phone_number(phone_number)

    @transaction.atomic
    def create_customer(
        self, phone_number, first_name, company_id, bot_access=False, is_active=True
    ):
        """
        Create a new customer account with profile.
        Customers authenticate via Telegram only (no password needed).

        Args:
            phone_number: Customer's phone number
            first_name: Customer's first name or company name
            company_id: ID of the company this customer belongs to (required)
            bot_access: Whether to grant bot access immediately (default: False)
            is_active: Whether customer account is active (default: True)

        Returns:
            CustomUser instance (with user_type='customer')

        Raises:
            BusinessLogicError: If customer with this phone already exists or company not found
        """
        # Validate company exists and is active
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise BusinessLogicError(
                message="Компания не найдена",
                error_code="COMPANY_NOT_FOUND",
                details={"company_id": company_id},
            )

        if not company.is_active:
            raise BusinessLogicError(
                message="Компания деактивирована",
                error_code="COMPANY_INACTIVE",
                details={"company_id": company_id, "company_name": company.name},
            )

        # Validate phone number
        phone_number = self.validate_phone_number(phone_number)

        # Check if phone already exists in CustomerProfile
        if CustomerProfile.objects.filter(phone_number=phone_number).exists():
            raise BusinessLogicError(
                message=f"Клиент с номером {phone_number} уже существует",
                error_code="CUSTOMER_ALREADY_EXISTS",
                details={"phone_number": phone_number},
            )

        # Also check ManagerProfile (phone must be unique across all profiles)
        if ManagerProfile.objects.filter(phone_number=phone_number).exists():
            raise BusinessLogicError(
                message=f"Номер {phone_number} уже используется менеджером",
                error_code="PHONE_ALREADY_USED",
                details={"phone_number": phone_number},
            )

        # Also check legacy fields (during migration)
        if CustomUser.objects.filter(phone_number=phone_number).exists():
            raise BusinessLogicError(
                message=f"Номер {phone_number} уже используется другим пользователем",
                error_code="PHONE_ALREADY_USED",
                details={"phone_number": phone_number},
            )

        # Auto-generate username from phone_number
        username = f"cust_{phone_number}"

        # Create customer (as CustomUser with user_type='customer')
        # Write to legacy fields for backward compatibility
        customer = CustomUser.objects.create(
            phone_number=phone_number,  # LEGACY - remove after migration
            first_name=first_name,
            company=company,  # LEGACY - remove after migration
            bot_access=bot_access,  # LEGACY - remove after migration
            is_active=is_active,
            user_type="customer",
            username=username,
        )

        # Create CustomerProfile (new canonical location for customer data)
        CustomerProfile.objects.create(
            user=customer,
            phone_number=phone_number,
            company=company,  # Required for CustomerProfile
            bot_access=bot_access,
        )

        self.logger.info(
            f"Created customer with profile: {customer.first_name} ({phone_number}) for company {company.name}"
        )
        return customer

    def get_customer_by_phone(self, phone_number):
        """
        Get customer by phone number.
        Searches CustomerProfile first, then falls back to legacy fields.

        Args:
            phone_number: Phone number to search for

        Returns:
            CustomUser instance (customer) or None
        """
        try:
            phone_number = self.validate_phone_number(phone_number)
        except BusinessLogicError:
            return None

        # Search CustomerProfile first
        try:
            profile = CustomerProfile.objects.select_related('user').get(
                phone_number=phone_number
            )
            return profile.user
        except CustomerProfile.DoesNotExist:
            pass

        # Fallback to legacy field
        try:
            return CustomUser.objects.get(
                phone_number=phone_number, user_type="customer"
            )
        except CustomUser.DoesNotExist:
            return None

    def get_customer_by_telegram_id(self, telegram_user_id):
        """
        Get customer by Telegram user ID.
        Searches CustomerProfile first, then falls back to legacy fields.

        Args:
            telegram_user_id: Telegram user ID to search for

        Returns:
            CustomUser instance (customer) or None
        """
        # Search CustomerProfile first
        try:
            profile = CustomerProfile.objects.select_related('user').get(
                telegram_user_id=telegram_user_id
            )
            return profile.user
        except CustomerProfile.DoesNotExist:
            pass

        # Fallback to legacy field
        try:
            return CustomUser.objects.get(
                telegram_user_id=telegram_user_id, user_type="customer"
            )
        except CustomUser.DoesNotExist:
            return None

    @transaction.atomic
    def activate_telegram_customer(
        self, phone_number, telegram_user_id, telegram_username=""
    ):
        """
        Link Telegram account to customer account.
        Called when customer first shares phone number in bot.

        Writes to both profile and legacy CustomUser fields for backward compatibility.

        Args:
            phone_number: Phone number shared by customer
            telegram_user_id: Telegram user ID
            telegram_username: Telegram username (optional)

        Returns:
            tuple: (CustomUser instance, str status)
                   status: 'has_access', 'no_access', 'needs_phone'

        Raises:
            BusinessLogicError: If phone not found or already linked to different account
        """
        # Validate phone number
        phone_number = self.validate_phone_number(phone_number)

        # Find customer by phone
        customer = self.get_customer_by_phone(phone_number)
        if not customer:
            # Phone not registered as customer
            return None, "needs_phone"

        # Check if this telegram_user_id is already linked to a different profile
        existing_customer = CustomerProfile.objects.filter(
            telegram_user_id=telegram_user_id
        ).exclude(user_id=customer.id).first()

        existing_manager = ManagerProfile.objects.filter(
            telegram_user_id=telegram_user_id
        ).exclude(user_id=customer.id).first()

        # Also check legacy field
        existing_legacy = CustomUser.objects.filter(
            telegram_user_id=telegram_user_id
        ).exclude(id=customer.id).first()

        existing = existing_customer or existing_manager or existing_legacy
        if existing:
            if hasattr(existing, 'user'):
                existing_name = existing.user.username or existing.user.first_name
            else:
                existing_name = existing.username or existing.first_name
            raise BusinessLogicError(
                message=f"Этот Telegram аккаунт уже привязан к другому пользователю: {existing_name}",
                error_code="TELEGRAM_ALREADY_LINKED",
                details={
                    "telegram_user_id": telegram_user_id,
                    "linked_to": existing_name,
                },
            )

        # Check if customer is active
        if not customer.is_active:
            raise BusinessLogicError(
                message="Ваш аккаунт деактивирован. Обратитесь к администратору.",
                error_code="CUSTOMER_DEACTIVATED",
                details={"phone_number": phone_number},
            )

        # Update profile if exists
        profile = customer.get_profile()
        if profile:
            profile.telegram_user_id = telegram_user_id
            profile.telegram_username = telegram_username
            profile.save()
            bot_access = profile.bot_access
        else:
            bot_access = customer.bot_access

        # Also update legacy CustomUser fields for backward compatibility
        customer.telegram_user_id = telegram_user_id
        customer.telegram_username = telegram_username
        customer.save()

        self.logger.info(
            f"Linked Telegram account {telegram_user_id} (@{telegram_username}) to customer {customer.first_name}"
        )

        # Return status based on access
        if bot_access:
            return customer, "has_access"
        else:
            return customer, "no_access"

    def get_active_customers(self):
        """
        Get all active customers with bot access.

        Returns:
            QuerySet of CustomUser instances (customers)
        """
        # Query via CustomerProfile for accuracy
        profile_user_ids = CustomerProfile.objects.filter(
            bot_access=True,
            user__is_active=True,
        ).values_list('user_id', flat=True)

        # Also include legacy customers without profiles
        return CustomUser.objects.filter(
            user_type="customer",
            is_active=True,
        ).filter(
            # Has profile with bot_access OR legacy bot_access
            models.Q(id__in=profile_user_ids) |
            models.Q(customer_profile__isnull=True, bot_access=True)
        ).order_by("-created_at")

    def get_pending_customers(self):
        """
        Get customers awaiting bot access approval.

        Returns:
            QuerySet of CustomUser instances (customers without bot_access but with telegram linked)
        """
        # Query via CustomerProfile
        profile_user_ids = CustomerProfile.objects.filter(
            bot_access=False,
            telegram_user_id__isnull=False,
            user__is_active=True,
        ).values_list('user_id', flat=True)

        # Also include legacy customers
        return CustomUser.objects.filter(
            user_type="customer",
            is_active=True,
        ).filter(
            models.Q(id__in=profile_user_ids) |
            models.Q(
                customer_profile__isnull=True,
                bot_access=False,
                telegram_user_id__isnull=False
            )
        ).order_by("-created_at")

    @transaction.atomic
    def grant_access(self, customer_id):
        """
        Grant bot access to customer.
        Updates both profile and legacy fields.

        Args:
            customer_id: Customer ID

        Returns:
            CustomUser customer instance

        Raises:
            BusinessLogicError: If customer not found
        """
        try:
            customer = CustomUser.objects.get(id=customer_id, user_type="customer")
        except CustomUser.DoesNotExist:
            raise BusinessLogicError(
                message="Клиент не найден",
                error_code="CUSTOMER_NOT_FOUND",
                details={"customer_id": customer_id},
            )

        # Update profile if exists
        profile = customer.get_profile()
        if profile:
            profile.bot_access = True
            profile.save()

        # Update legacy field
        customer.bot_access = True
        customer.save()

        self.logger.info(f"Granted bot access to customer: {customer.first_name}")
        return customer

    @transaction.atomic
    def revoke_access(self, customer_id):
        """
        Revoke bot access from customer.
        Updates both profile and legacy fields.

        Args:
            customer_id: Customer ID

        Returns:
            CustomUser customer instance

        Raises:
            BusinessLogicError: If customer not found
        """
        try:
            customer = CustomUser.objects.get(id=customer_id, user_type="customer")
        except CustomUser.DoesNotExist:
            raise BusinessLogicError(
                message="Клиент не найден",
                error_code="CUSTOMER_NOT_FOUND",
                details={"customer_id": customer_id},
            )

        # Update profile if exists
        profile = customer.get_profile()
        if profile:
            profile.bot_access = False
            profile.save()

        # Update legacy field
        customer.bot_access = False
        customer.save()

        self.logger.info(f"Revoked bot access from customer: {customer.first_name}")
        return customer

    @transaction.atomic
    def update_customer(self, customer_id, **kwargs):
        """
        Update customer information.
        Writes to both profile and legacy fields for backward compatibility.

        Args:
            customer_id: Customer ID to update
            **kwargs: Fields to update (first_name, phone_number, company_id, is_active, bot_access)

        Returns:
            CustomUser customer instance

        Raises:
            BusinessLogicError: If customer not found or invalid fields
        """
        try:
            customer = CustomUser.objects.get(id=customer_id, user_type="customer")
        except CustomUser.DoesNotExist:
            raise BusinessLogicError(
                message="Клиент не найден",
                error_code="CUSTOMER_NOT_FOUND",
                details={"customer_id": customer_id},
            )

        # Get or create profile
        # For customers, we need a company - CustomerProfile.company is NOT NULL
        # Check profile company first, then legacy field
        profile = customer.get_profile()
        existing_company = None
        if profile:
            existing_company = profile.company
        if existing_company is None:
            existing_company = customer.company

        # If customer has no company anywhere, require company_id in kwargs
        if existing_company is None:
            if 'company_id' not in kwargs and 'company' not in kwargs:
                raise BusinessLogicError(
                    message="Клиент должен быть привязан к компании. Укажите company_id.",
                    error_code="COMPANY_REQUIRED",
                    details={"customer_id": customer_id},
                )
            # Get company from kwargs for profile creation
            company_id = kwargs.get('company_id') or (kwargs.get('company').id if kwargs.get('company') else None)
            if company_id:
                try:
                    existing_company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    raise BusinessLogicError(
                        message="Компания не найдена",
                        error_code="COMPANY_NOT_FOUND",
                        details={"company_id": company_id},
                    )

        profile, created = CustomerProfile.objects.get_or_create(
            user=customer,
            defaults={
                'phone_number': customer.phone_number or f"+0{customer_id}",
                'telegram_user_id': customer.telegram_user_id,
                'telegram_username': customer.telegram_username,
                'bot_access': customer.bot_access,
                'company': existing_company,
            }
        )

        # Validate and update phone number if provided
        if "phone_number" in kwargs:
            new_phone = self.validate_phone_number(kwargs["phone_number"])

            # Check if new phone is already taken by another profile
            if CustomerProfile.objects.filter(phone_number=new_phone).exclude(user_id=customer_id).exists():
                raise BusinessLogicError(
                    message=f"Номер {new_phone} уже используется",
                    error_code="PHONE_ALREADY_EXISTS",
                    details={"phone_number": new_phone},
                )

            # Also check ManagerProfile
            if ManagerProfile.objects.filter(phone_number=new_phone).exists():
                raise BusinessLogicError(
                    message=f"Номер {new_phone} уже используется менеджером",
                    error_code="PHONE_ALREADY_EXISTS",
                    details={"phone_number": new_phone},
                )

            # Also check legacy field
            if CustomUser.objects.filter(phone_number=new_phone).exclude(id=customer_id).exists():
                raise BusinessLogicError(
                    message=f"Номер {new_phone} уже используется",
                    error_code="PHONE_ALREADY_EXISTS",
                    details={"phone_number": new_phone},
                )

            profile.phone_number = new_phone
            customer.phone_number = new_phone  # LEGACY

        # Validate and update company if provided (handles both company_id and company object)
        if "company_id" in kwargs or "company" in kwargs:
            if "company" in kwargs:
                # Company object passed directly (from serializer with source='company')
                company = kwargs["company"]
            else:
                # company_id passed
                company_id = kwargs["company_id"]
                try:
                    company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    raise BusinessLogicError(
                        message="Компания не найдена",
                        error_code="COMPANY_NOT_FOUND",
                        details={"company_id": company_id},
                    )

            if not company.is_active:
                raise BusinessLogicError(
                    message="Компания деактивирована",
                    error_code="COMPANY_INACTIVE",
                    details={"company_id": company.id, "company_name": company.name},
                )
            profile.company = company
            customer.company = company  # LEGACY

        # Update profile fields
        if "bot_access" in kwargs:
            profile.bot_access = kwargs["bot_access"]
            customer.bot_access = kwargs["bot_access"]  # LEGACY

        # Update CustomUser fields
        user_fields = ["first_name", "is_active"]
        for field in user_fields:
            if field in kwargs:
                setattr(customer, field, kwargs[field])

        profile.save()
        customer.save()

        self.logger.info(
            f"Updated customer {customer.first_name}: {list(kwargs.keys())}"
        )
        return customer

    def deactivate_customer(self, customer_id):
        """
        Deactivate customer account (soft delete).

        Args:
            customer_id: Customer ID

        Returns:
            CustomUser customer instance
        """
        return self.update_customer(customer_id, is_active=False, bot_access=False)
