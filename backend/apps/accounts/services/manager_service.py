import re

from django.db import models, transaction

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService

from ..models import CustomerProfile, CustomUser, ManagerProfile


class ManagerService(BaseService):
    """
    Business logic for Manager model and Telegram bot access control.

    NOTE: This service is being migrated to use ManagerProfile instead of
    legacy fields on CustomUser. During migration, it writes to both
    ManagerProfile AND legacy CustomUser fields for backward compatibility.
    """

    def validate_phone_number(self, phone_number):
        """
        Validate phone number format.

        Args:
            phone_number: Phone number string to validate

        Returns:
            Cleaned phone number

        Raises:
            BusinessLogicError: If phone number format is invalid
        """
        # Clean the phone number
        cleaned = phone_number.strip()

        # Validate format using regex
        pattern = r"^\+?1?\d{9,15}$"
        if not re.match(pattern, cleaned):
            raise BusinessLogicError(
                message="Неверный формат номера телефона. Используйте формат: +998901234567 (9-15 цифр)",
                error_code="INVALID_PHONE_FORMAT",
                details={"phone_number": phone_number},
            )

        # Ensure it starts with '+'
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned

        return cleaned

    @transaction.atomic
    def create_manager(
        self,
        phone_number,
        first_name,
        bot_access=False,
        gate_access=False,
        is_active=True,
        password=None,
        company_id=None,
    ):
        """
        Create a new manager with profile.

        Args:
            phone_number: Manager's phone number
            first_name: Manager's first name
            bot_access: Whether to grant bot access immediately (default: False)
            gate_access: Whether to grant gate access immediately (default: False)
            is_active: Whether manager account is active (default: True)
            password: Optional password (will be hashed)
            company_id: Optional company ID to link manager to

        Returns:
            CustomUser instance (with user_type='manager')

        Raises:
            BusinessLogicError: If manager with this phone already exists
        """
        # Validate phone number
        phone_number = self.validate_phone_number(phone_number)

        # Check if phone already exists in ManagerProfile
        if ManagerProfile.objects.filter(phone_number=phone_number).exists():
            raise BusinessLogicError(
                message=f"Менеджер с номером {phone_number} уже существует",
                error_code="MANAGER_ALREADY_EXISTS",
                details={"phone_number": phone_number},
            )

        # Also check legacy field (during migration)
        if CustomUser.objects.filter(
            phone_number=phone_number, user_type="manager"
        ).exists():
            raise BusinessLogicError(
                message=f"Менеджер с номером {phone_number} уже существует",
                error_code="MANAGER_ALREADY_EXISTS",
                details={"phone_number": phone_number},
            )

        # Validate company if provided
        company = None
        if company_id:
            from ..models import Company
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
                    details={"company_id": company_id},
                )

        # Auto-generate username from phone_number
        username = f"mgr_{phone_number}"

        # Create manager (as CustomUser with user_type='manager')
        # Write to legacy fields for backward compatibility
        manager = CustomUser.objects.create(
            phone_number=phone_number,  # LEGACY - remove after migration
            first_name=first_name,
            bot_access=bot_access,  # LEGACY - remove after migration
            gate_access=gate_access,  # LEGACY - remove after migration
            is_active=is_active,
            user_type="manager",
            username=username,
            company=company,  # LEGACY - remove after migration
        )

        # Set password if provided
        if password:
            manager.set_password(password)
            manager.save()

        # Create ManagerProfile (new canonical location for manager data)
        ManagerProfile.objects.create(
            user=manager,
            phone_number=phone_number,
            bot_access=bot_access,
            gate_access=gate_access,
            company=company,
        )

        self.logger.info(f"Created manager with profile: {manager.first_name} ({phone_number})")
        return manager

    def get_user_by_phone(self, phone_number):
        """
        Get any user (admin, manager, or customer) by phone number.
        Searches profiles first, then falls back to legacy CustomUser fields.

        Args:
            phone_number: Phone number to search for

        Returns:
            CustomUser instance or None
        """
        try:
            phone_number = self.validate_phone_number(phone_number)
        except BusinessLogicError:
            return None

        # Search ManagerProfile first
        try:
            profile = ManagerProfile.objects.select_related('user').get(
                phone_number=phone_number
            )
            return profile.user
        except ManagerProfile.DoesNotExist:
            pass

        # Search CustomerProfile
        try:
            profile = CustomerProfile.objects.select_related('user').get(
                phone_number=phone_number
            )
            return profile.user
        except CustomerProfile.DoesNotExist:
            pass

        # Fallback to legacy CustomUser field
        try:
            return CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            return None

    def get_manager_by_phone(self, phone_number):
        """
        Get manager by phone number.
        DEPRECATED: Use get_user_by_phone() for unified access.

        Args:
            phone_number: Phone number to search for

        Returns:
            CustomUser instance (manager) or None
        """
        try:
            phone_number = self.validate_phone_number(phone_number)
        except BusinessLogicError:
            return None

        # Search ManagerProfile first
        try:
            profile = ManagerProfile.objects.select_related('user').get(
                phone_number=phone_number
            )
            return profile.user
        except ManagerProfile.DoesNotExist:
            pass

        # Fallback to legacy field
        try:
            return CustomUser.objects.get(
                phone_number=phone_number, user_type="manager"
            )
        except CustomUser.DoesNotExist:
            return None

    def get_user_by_telegram_id(self, telegram_user_id):
        """
        Get any user (admin, manager, or customer) by Telegram user ID.
        Searches profiles first, then falls back to legacy CustomUser fields.

        Args:
            telegram_user_id: Telegram user ID to search for

        Returns:
            CustomUser instance or None
        """
        # Search ManagerProfile first
        try:
            profile = ManagerProfile.objects.select_related('user').get(
                telegram_user_id=telegram_user_id
            )
            return profile.user
        except ManagerProfile.DoesNotExist:
            pass

        # Search CustomerProfile
        try:
            profile = CustomerProfile.objects.select_related('user').get(
                telegram_user_id=telegram_user_id
            )
            return profile.user
        except CustomerProfile.DoesNotExist:
            pass

        # Fallback to legacy CustomUser field
        try:
            return CustomUser.objects.get(telegram_user_id=telegram_user_id)
        except CustomUser.DoesNotExist:
            return None

    def get_manager_by_telegram_id(self, telegram_user_id):
        """
        Get manager by Telegram user ID.
        DEPRECATED: Use get_user_by_telegram_id() for unified access.

        Args:
            telegram_user_id: Telegram user ID to search for

        Returns:
            CustomUser instance (manager) or None
        """
        # Search ManagerProfile first
        try:
            profile = ManagerProfile.objects.select_related('user').get(
                telegram_user_id=telegram_user_id
            )
            return profile.user
        except ManagerProfile.DoesNotExist:
            pass

        # Fallback to legacy field
        try:
            return CustomUser.objects.get(
                telegram_user_id=telegram_user_id, user_type="manager"
            )
        except CustomUser.DoesNotExist:
            return None

    @transaction.atomic
    def activate_telegram_user(
        self, phone_number, telegram_user_id, telegram_username=""
    ):
        """
        Link Telegram account to user account (admin, manager, or customer).
        Called when user first shares phone number in bot.

        Writes to both profile and legacy CustomUser fields for backward compatibility.

        Args:
            phone_number: Phone number shared by user
            telegram_user_id: Telegram user ID
            telegram_username: Telegram username (optional)

        Returns:
            tuple: (CustomUser instance, dict with status info)

        Raises:
            BusinessLogicError: If phone not found or already linked to different account
        """
        # Validate phone number
        phone_number = self.validate_phone_number(phone_number)

        # Find user by phone (admin, manager, or customer)
        user = self.get_user_by_phone(phone_number)
        if not user:
            raise BusinessLogicError(
                message="Номер телефона не зарегистрирован. Обратитесь к администратору для регистрации.",
                error_code="PHONE_NOT_REGISTERED",
                details={"phone_number": phone_number},
            )

        # Check if this telegram_user_id is already linked to a different profile
        existing_manager = ManagerProfile.objects.filter(
            telegram_user_id=telegram_user_id
        ).exclude(user_id=user.id).first()

        existing_customer = CustomerProfile.objects.filter(
            telegram_user_id=telegram_user_id
        ).exclude(user_id=user.id).first()

        # Also check legacy field
        existing_legacy = CustomUser.objects.filter(
            telegram_user_id=telegram_user_id
        ).exclude(id=user.id).first()

        existing = existing_manager or existing_customer or existing_legacy
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

        # Check if user is active
        if not user.is_active:
            raise BusinessLogicError(
                message="Ваш аккаунт деактивирован. Обратитесь к администратору.",
                error_code="USER_DEACTIVATED",
                details={"phone_number": phone_number},
            )

        # Update profile if exists
        profile = user.get_profile()
        was_already_linked = False

        if profile:
            was_already_linked = profile.telegram_user_id is not None
            profile.telegram_user_id = telegram_user_id
            profile.telegram_username = telegram_username
            profile.save()
            bot_access = profile.bot_access
            can_use_bot = profile.can_use_bot
        else:
            # No profile (admin user or legacy user without profile)
            was_already_linked = user.telegram_user_id is not None
            bot_access = user.bot_access
            can_use_bot = user.can_use_bot

        # Also update legacy CustomUser fields for backward compatibility
        user.telegram_user_id = telegram_user_id
        user.telegram_username = telegram_username
        user.save()

        self.logger.info(
            f"Linked Telegram account {telegram_user_id} (@{telegram_username}) to {user.user_type} {user.username or user.first_name}"
        )

        return user, {
            "already_linked": was_already_linked,
            "has_access": bot_access,
            "can_use_bot": can_use_bot,
        }

    def get_active_managers(self):
        """
        Get all active managers with bot access.

        Returns:
            QuerySet of CustomUser instances (managers)
        """
        # Query via ManagerProfile for accuracy
        profile_user_ids = ManagerProfile.objects.filter(
            bot_access=True,
            user__is_active=True,
        ).values_list('user_id', flat=True)

        # Also include legacy managers without profiles
        return CustomUser.objects.filter(
            user_type="manager",
            is_active=True,
        ).filter(
            # Has profile with bot_access OR legacy bot_access
            models.Q(id__in=profile_user_ids) |
            models.Q(manager_profile__isnull=True, bot_access=True)
        ).order_by("-created_at")

    @transaction.atomic
    def update_manager(self, manager_id, **kwargs):
        """
        Update manager information.
        Writes to both profile and legacy fields for backward compatibility.

        Args:
            manager_id: Manager ID to update
            **kwargs: Fields to update (first_name, phone_number, password, is_active, bot_access, gate_access, company_id)

        Returns:
            CustomUser manager instance

        Raises:
            BusinessLogicError: If manager not found or invalid fields
        """
        try:
            manager = CustomUser.objects.get(id=manager_id, user_type="manager")
        except CustomUser.DoesNotExist:
            raise BusinessLogicError(
                message="Менеджер не найден",
                error_code="MANAGER_NOT_FOUND",
                details={"manager_id": manager_id},
            )

        # Get or create profile
        profile, _ = ManagerProfile.objects.get_or_create(
            user=manager,
            defaults={
                'phone_number': manager.phone_number or f"+0{manager_id}",
                'telegram_user_id': manager.telegram_user_id,
                'telegram_username': manager.telegram_username,
                'bot_access': manager.bot_access,
                'gate_access': manager.gate_access,
                'company': manager.company,
            }
        )

        # Validate and update phone number if provided
        if "phone_number" in kwargs:
            new_phone = self.validate_phone_number(kwargs["phone_number"])

            # Check if new phone is already taken by another profile
            if ManagerProfile.objects.filter(phone_number=new_phone).exclude(user_id=manager_id).exists():
                raise BusinessLogicError(
                    message=f"Номер {new_phone} уже используется другим менеджером",
                    error_code="PHONE_ALREADY_EXISTS",
                    details={"phone_number": new_phone},
                )

            # Also check legacy field
            if CustomUser.objects.filter(
                phone_number=new_phone, user_type="manager"
            ).exclude(id=manager_id).exists():
                raise BusinessLogicError(
                    message=f"Номер {new_phone} уже используется другим менеджером",
                    error_code="PHONE_ALREADY_EXISTS",
                    details={"phone_number": new_phone},
                )

            profile.phone_number = new_phone
            manager.phone_number = new_phone  # LEGACY

        # Update password if provided
        if kwargs.get("password"):
            manager.set_password(kwargs["password"])

        # Update company if provided
        if "company_id" in kwargs:
            company_id = kwargs["company_id"]
            if company_id:
                from ..models import Company
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
                        details={"company_id": company_id},
                    )
                profile.company = company
                manager.company = company  # LEGACY
            else:
                profile.company = None
                manager.company = None  # LEGACY

        # Update profile fields
        profile_fields = ["bot_access", "gate_access"]
        for field in profile_fields:
            if field in kwargs:
                setattr(profile, field, kwargs[field])
                setattr(manager, field, kwargs[field])  # LEGACY

        # Update CustomUser fields
        user_fields = ["first_name", "is_active"]
        for field in user_fields:
            if field in kwargs:
                setattr(manager, field, kwargs[field])

        profile.save()
        manager.save()

        self.logger.info(f"Updated manager {manager.first_name}: {list(kwargs.keys())}")
        return manager

    @transaction.atomic
    def grant_access(self, manager_id):
        """
        Grant bot access to manager.

        Args:
            manager_id: Manager ID

        Returns:
            CustomUser instance

        Raises:
            BusinessLogicError: If manager not found
        """
        return self.update_manager(manager_id, bot_access=True)

    @transaction.atomic
    def revoke_access(self, manager_id):
        """
        Revoke bot access from manager.

        Args:
            manager_id: Manager ID

        Returns:
            CustomUser instance

        Raises:
            BusinessLogicError: If manager not found
        """
        return self.update_manager(manager_id, bot_access=False)

    @transaction.atomic
    def delete_manager(self, manager_id):
        """
        Soft delete manager (set is_active=False).

        Args:
            manager_id: Manager ID

        Returns:
            CustomUser instance

        Raises:
            BusinessLogicError: If manager not found
        """
        return self.update_manager(manager_id, is_active=False, bot_access=False)
