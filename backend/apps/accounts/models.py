from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import TimestampedModel


class CustomUser(AbstractUser, TimestampedModel):
    """
    Unified user model for API users, Telegram bot managers, and customers.
    Uses user_type field to distinguish between:
    - 'admin': API users with username login
    - 'manager': Terminal staff using Telegram bot at gates
    - 'customer': External customers creating pre-orders via Telegram bot

    NOTE: Manager/customer-specific fields (phone, telegram, etc.) are being
    migrated to ManagerProfile/CustomerProfile models. The fields here are
    kept for backward compatibility during migration.
    """

    # User type field
    USER_TYPE_CHOICES = [
        ("admin", "API User"),
        ("manager", "Telegram Manager"),
        ("customer", "Customer"),
    ]
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default="admin",
        help_text="User type determines access method: admin (API with username) or manager (Telegram with phone)",
    )

    # Keep existing admin field for API user privileges
    is_admin = models.BooleanField(default=False)

    # ==========================================================================
    # LEGACY FIELDS - Being migrated to ManagerProfile/CustomerProfile
    # These fields will be removed after full migration to profile models.
    # Use profile.phone_number, profile.telegram_user_id, etc. for new code.
    # ==========================================================================
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[],  # Validation moved to profile models
        verbose_name="[LEGACY] Номер телефона",
    )
    telegram_user_id = models.BigIntegerField(
        null=True, blank=True, unique=True, verbose_name="[LEGACY] Telegram User ID"
    )
    telegram_username = models.CharField(
        max_length=255, blank=True, default="", verbose_name="[LEGACY] Telegram Username"
    )
    bot_access = models.BooleanField(default=False, verbose_name="[LEGACY] Доступ к боту")
    language = models.CharField(
        max_length=5,
        choices=[("ru", "Русский"), ("uz", "O'zbekcha")],
        default="ru",
        verbose_name="[LEGACY] Язык уведомлений",
    )
    gate_access = models.BooleanField(default=False, verbose_name="[LEGACY] Доступ к воротам")
    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="[LEGACY] Компания",
        help_text="LEGACY - use profile.company instead",
    )
    # ==========================================================================

    class Meta:
        indexes = [
            models.Index(fields=["user_type"]),
            models.Index(fields=["phone_number"]),
            models.Index(fields=["telegram_user_id"]),
        ]

    def __str__(self):
        if self.user_type in ("manager", "customer") and self.phone_number:
            return f"{self.first_name} ({self.phone_number})"
        return self.username or f"User {self.id}"

    # Bot access properties (works for all user types)
    @property
    def can_use_bot(self):
        """Check if user can currently use the Telegram bot."""
        return self.is_active and self.bot_access and self.telegram_user_id is not None

    @property
    def full_name(self):
        """Return user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username

    @property
    def has_telegram_linked(self):
        """Check if manager has Telegram account linked."""
        return self.telegram_user_id is not None

    def check_password(self, raw_password):
        """Check if raw password matches hashed password (inherited from AbstractUser)."""
        return super().check_password(raw_password)

    # ==========================================================================
    # PROFILE ACCESS HELPERS - Use these for new code during migration
    # ==========================================================================

    def get_profile(self):
        """
        Get the appropriate profile for this user based on user_type.

        Returns:
            ManagerProfile | CustomerProfile | None: The profile, or None for admins
            or if profile doesn't exist yet.

        Usage:
            profile = user.get_profile()
            if profile:
                phone = profile.phone_number
        """
        # NOTE: Django OneToOne reverse relations raise DoesNotExist (not AttributeError)
        # when the related object doesn't exist. getattr() only catches AttributeError,
        # so we must use try/except to handle missing profiles gracefully.
        if self.user_type == "manager":
            try:
                return self.manager_profile
            except ManagerProfile.DoesNotExist:
                return None
        elif self.user_type == "customer":
            try:
                return self.customer_profile
            except CustomerProfile.DoesNotExist:
                return None
        return None

    def has_profile(self):
        """Check if user has a profile created."""
        return self.get_profile() is not None

    @property
    def profile_phone_number(self):
        """Get phone number from profile (preferred) or legacy field."""
        profile = self.get_profile()
        if profile:
            return profile.phone_number
        return self.phone_number  # Fallback to legacy field

    @property
    def profile_telegram_user_id(self):
        """Get telegram_user_id from profile (preferred) or legacy field."""
        profile = self.get_profile()
        if profile:
            return profile.telegram_user_id
        return self.telegram_user_id  # Fallback to legacy field

    @property
    def profile_bot_access(self):
        """Get bot_access from profile (preferred) or legacy field."""
        profile = self.get_profile()
        if profile:
            return profile.bot_access
        return self.bot_access  # Fallback to legacy field

    @property
    def profile_company(self):
        """Get company from profile (preferred) or legacy field."""
        profile = self.get_profile()
        if profile:
            return profile.company
        return self.company  # Fallback to legacy field


# Shared validators (used by both CustomUser legacy fields and Profile models)
phone_regex = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message="Номер телефона должен быть в формате: '+998901234567'. До 15 цифр.",
)

LANGUAGE_CHOICES = [
    ("ru", "Русский"),
    ("uz", "O'zbekcha"),
]


class ManagerProfile(TimestampedModel):
    """
    Profile for manager users with terminal/bot access.
    Managers are terminal staff who use the Telegram bot at gates.
    """

    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="manager_profile",
        limit_choices_to={"user_type": "manager"},
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_regex],
        verbose_name="Номер телефона",
    )
    telegram_user_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name="Telegram User ID",
    )
    telegram_username = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Telegram Username",
    )
    bot_access = models.BooleanField(
        default=False,
        verbose_name="Доступ к боту",
    )
    gate_access = models.BooleanField(
        default=False,
        verbose_name="Доступ к воротам",
    )
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="ru",
        verbose_name="Язык уведомлений",
    )
    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="managers",
        verbose_name="Компания",
    )

    class Meta:
        verbose_name = "Профиль менеджера"
        verbose_name_plural = "Профили менеджеров"
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["telegram_user_id"]),
        ]

    def __str__(self):
        return f"{self.user.first_name} ({self.phone_number})"

    @property
    def can_use_bot(self):
        """Check if manager can currently use the Telegram bot."""
        return self.user.is_active and self.bot_access and self.telegram_user_id is not None

    @property
    def has_telegram_linked(self):
        """Check if manager has Telegram account linked."""
        return self.telegram_user_id is not None


class CustomerProfile(TimestampedModel):
    """
    Profile for customer users with pre-order access.
    Customers are external businesses creating pre-orders via Telegram bot.
    """

    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="customer_profile",
        limit_choices_to={"user_type": "customer"},
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_regex],
        verbose_name="Номер телефона",
    )
    telegram_user_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name="Telegram User ID",
    )
    telegram_username = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Telegram Username",
    )
    bot_access = models.BooleanField(
        default=False,
        verbose_name="Доступ к боту",
    )
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="ru",
        verbose_name="Язык уведомлений",
    )
    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        related_name="customers",
        verbose_name="Компания",
    )  # NOT NULL - required for customers

    class Meta:
        verbose_name = "Профиль клиента"
        verbose_name_plural = "Профили клиентов"
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["telegram_user_id"]),
        ]

    def __str__(self):
        return f"{self.user.first_name} ({self.phone_number})"

    @property
    def can_use_bot(self):
        """Check if customer can currently use the Telegram bot."""
        return self.user.is_active and self.bot_access and self.telegram_user_id is not None

    @property
    def has_telegram_linked(self):
        """Check if customer has Telegram account linked."""
        return self.telegram_user_id is not None


class BillingMethod(models.TextChoices):
    """Billing method for monthly statements."""

    SPLIT = "split", "Раздельный расчёт"
    EXIT_MONTH = "exit_month", "По месяцу выхода"


class Company(TimestampedModel):
    """
    Company model representing terminal customers (businesses).
    Companies can be linked to customer users for pre-orders and vehicle entries.
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Название компании",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name="Slug",
        help_text="URL-friendly identifier, auto-generated from name",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
    )

    # Telegram notification settings
    telegram_group_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Telegram группа",
        help_text="Username (@mygroup) или ID группы (-1001234567890)",
    )
    telegram_group_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Название группы",
        help_text="Название группы для отображения",
    )
    notifications_enabled = models.BooleanField(
        default=False,
        verbose_name="Уведомления включены",
        help_text="Отправлять уведомления в Telegram при создании записей контейнеров",
    )
    billing_method = models.CharField(
        max_length=20,
        choices=BillingMethod.choices,
        default=BillingMethod.SPLIT,
        verbose_name="Метод расчёта",
        help_text="Метод расчёта для ежемесячных выписок",
    )

    # Legal / billing credentials (buyer side for Счёт-фактура)
    legal_address = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Юридический адрес",
    )
    inn = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="ИНН",
    )
    mfo = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="МФО",
    )
    bank_account = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Расчётный счёт",
    )
    bank_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Банк",
    )

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Company.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
