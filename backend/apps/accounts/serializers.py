from django.contrib.auth import authenticate
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from .models import Company, CustomerProfile, CustomUser, ManagerProfile


class UserSerializer(serializers.ModelSerializer):
    user_type = serializers.CharField(read_only=True)
    company = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_admin",
            "is_staff",
            "is_active",
            "user_type",
            "company",
        )
        read_only_fields = ("id", "is_staff", "is_active", "user_type", "company")

    def get_company(self, obj):
        """Get company from profile (preferred) or legacy field."""
        company = obj.profile_company
        if company:
            return {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
            }
        return None


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if not username or not password:
            raise serializers.ValidationError("Необходимо указать имя пользователя и пароль")

        user = authenticate(username=username, password=password)
        if not user:
            raise AuthenticationFailed("Неверные учётные данные")

        if not user.is_active:
            raise PermissionDenied("Учётная запись пользователя отключена")

        attrs["user"] = user
        return attrs


class UnifiedLoginSerializer(serializers.Serializer):
    """
    Unified login serializer for both CustomUser and Manager.
    Auto-detects which model based on input format:
    - +998... (phone) → Manager
    - text (username) → CustomUser
    """

    login = serializers.CharField()  # phone OR username
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        login = attrs.get("login")
        password = attrs.get("password")

        if not login or not password:
            raise serializers.ValidationError("Необходимо указать логин и пароль")

        user = None
        user_type = None

        # Auto-detect: is it a phone or username?
        if login.startswith("+") or (login[0].isdigit() and len(login) > 5):
            # Looks like phone → check Manager
            user = self._authenticate_manager(login, password)
            user_type = "manager"
        else:
            # Looks like username → check CustomUser (admin or customer)
            user = self._authenticate_custom_user(login, password)
            # Determine user_type based on actual user.user_type field
            if user and hasattr(user, "user_type"):
                if user.user_type == "customer":
                    user_type = "customer"
                elif user.user_type == "manager":
                    user_type = "manager"
                else:
                    user_type = "custom_user"  # admin or other types
            else:
                user_type = "custom_user"  # fallback for users without user_type

        if not user:
            raise AuthenticationFailed("Неверный логин или пароль")

        attrs["user"] = user
        attrs["user_type"] = user_type
        return attrs

    def _authenticate_manager(self, phone_number, password):
        """
        Authenticate manager (CustomUser with user_type='manager') by phone + password.
        Returns None if authentication fails for any reason.
        """
        try:
            manager = CustomUser.objects.get(phone_number=phone_number, user_type="manager")

            # Check password first
            if not manager.check_password(password):
                return None

            # Check if account is active
            if not manager.is_active:
                raise PermissionDenied("Учётная запись менеджера отключена")

            return manager

        except CustomUser.DoesNotExist:
            return None

    def _authenticate_custom_user(self, username, password):
        """
        Authenticate CustomUser by username + password.
        Returns None if authentication fails for any reason.
        """
        user = authenticate(username=username, password=password)

        if not user:
            return None

        if not user.is_active:
            raise PermissionDenied("Учётная запись пользователя отключена")

        return user


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
            "is_admin",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ManagerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for ManagerProfile model.
    """

    class Meta:
        model = ManagerProfile
        fields = (
            "phone_number",
            "telegram_user_id",
            "telegram_username",
            "bot_access",
            "gate_access",
            "language",
            "company",
        )
        read_only_fields = ("telegram_user_id", "telegram_username")


class ManagerSerializer(serializers.ModelSerializer):
    """
    Serializer for Manager users (CustomUser with user_type='manager').
    Reads from ManagerProfile when available, falls back to legacy fields.
    """

    can_use_bot = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    telegram_user_id = serializers.SerializerMethodField()
    telegram_username = serializers.SerializerMethodField()
    bot_access = serializers.SerializerMethodField()
    gate_access = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    has_profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "first_name",
            "phone_number",
            "telegram_user_id",
            "telegram_username",
            "bot_access",
            "gate_access",
            "is_active",
            "can_use_bot",
            "has_profile",
            "company",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "telegram_user_id",
            "telegram_username",
            "created_at",
            "updated_at",
        )

    def _get_profile(self, obj):
        """Get manager profile, using cached version if available."""
        if not hasattr(obj, "_cached_profile"):
            try:
                obj._cached_profile = obj.manager_profile
            except ManagerProfile.DoesNotExist:
                obj._cached_profile = None
        return obj._cached_profile

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_can_use_bot(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.can_use_bot
        return obj.can_use_bot

    @extend_schema_field(OpenApiTypes.STR)
    def get_phone_number(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.phone_number
        return obj.phone_number

    @extend_schema_field({"type": "integer", "nullable": True})
    def get_telegram_user_id(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.telegram_user_id
        return obj.telegram_user_id

    @extend_schema_field(OpenApiTypes.STR)
    def get_telegram_username(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.telegram_username
        return obj.telegram_username

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_bot_access(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.bot_access
        return obj.bot_access

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_gate_access(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.gate_access
        return obj.gate_access

    @extend_schema_field({"type": "object", "nullable": True})
    def get_company(self, obj):
        profile = self._get_profile(obj)
        company = profile.company if profile else obj.company
        if company:
            return CompanySerializer(company).data
        return None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_has_profile(self, obj):
        return self._get_profile(obj) is not None


class ManagerCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new manager with password.
    Phone validation is handled by the model's RegexValidator.
    telegram_user_id can be pre-populated to skip Telegram bot registration.
    """

    password = serializers.CharField(write_only=True, min_length=8, required=False)
    telegram_user_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "phone_number",
            "password",
            "bot_access",
            "gate_access",
            "is_active",
            "telegram_user_id",
        )

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        # Auto-generate username from phone_number for manager users
        phone_number = validated_data.get("phone_number")
        validated_data["username"] = f"mgr_{phone_number}" if phone_number else None
        validated_data["user_type"] = "manager"

        manager = CustomUser.objects.create(**validated_data)
        if password:
            manager.set_password(password)
            manager.save()
        return manager


class ManagerUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating manager information.
    Phone validation is handled by the model's RegexValidator.
    Password update is optional.
    telegram_user_id can be updated to link/unlink Telegram account.
    """

    password = serializers.CharField(write_only=True, min_length=8, required=False)
    telegram_user_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "phone_number",
            "password",
            "is_active",
            "bot_access",
            "gate_access",
            "telegram_user_id",
        )

    def validate_phone_number(self, value):
        """
        Validate phone_number is unique, excluding current instance.
        """
        # Get current instance being updated
        instance = self.instance

        # Check if phone_number is unique (excluding current instance)
        if instance and CustomUser.objects.filter(phone_number=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("Менеджер с таким номером телефона уже существует.")
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance


class ManagerStatsSerializer(serializers.Serializer):
    """
    Serializer for manager statistics.
    """

    total_managers = serializers.IntegerField()
    active_managers = serializers.IntegerField()
    managers_with_access = serializers.IntegerField()
    managers_with_telegram = serializers.IntegerField()


# ============ Company Serializers ============


class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer for Company model (read operations).
    Includes counts for customers and container entries.
    """

    customers_count = serializers.SerializerMethodField()
    entries_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "slug",
            "is_active",
            "telegram_group_id",
            "telegram_group_name",
            "notifications_enabled",
            "customers_count",
            "entries_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    @extend_schema_field(OpenApiTypes.INT)
    def get_customers_count(self, obj):
        """Count of customers linked to this company via CustomerProfile."""
        if hasattr(obj, "_customers_count"):
            return obj._customers_count
        return obj.customers.count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_entries_count(self, obj):
        """Count of container entries for this company."""
        if hasattr(obj, "_entries_count"):
            return obj._entries_count
        return obj.container_entries.count()


class CompanyCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new company.
    """

    class Meta:
        model = Company
        fields = ("name",)

    def validate_name(self, value):
        """Validate company name is unique."""
        if Company.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("Компания с таким названием уже существует.")
        return value.strip()


class CompanyUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating company information.
    """

    class Meta:
        model = Company
        fields = (
            "name",
            "is_active",
            "telegram_group_id",
            "telegram_group_name",
            "notifications_enabled",
        )

    def validate_name(self, value):
        """Validate company name is unique, excluding current instance."""
        instance = self.instance
        if instance and Company.objects.filter(name__iexact=value.strip()).exclude(id=instance.id).exists():
            raise serializers.ValidationError("Компания с таким названием уже существует.")
        return value.strip()

    def validate_telegram_group_id(self, value):
        """
        Validate and clean telegram_group_id.
        Accepts two formats:
        - Group ID: negative number like -1001234567890 (works for all groups)
        - Group Username: @username format (only for public groups with username)
        """
        import re

        if value is None:
            return value

        # Strip whitespace
        cleaned = value.strip() if value else None

        # Return None for empty strings
        if not cleaned:
            return None

        # Format 1: Group ID (negative number starting with -)
        if cleaned.startswith("-"):
            try:
                int(cleaned)
                return cleaned
            except ValueError:
                raise serializers.ValidationError("ID группы должен быть числом (например: -1001234567890)")

        # Format 2: Username (@groupname or groupname)
        # Normalize to include @ prefix
        if not cleaned.startswith("@"):
            cleaned = f"@{cleaned}"

        # Validate username format: @username (alphanumeric + underscores, 5-32 chars)
        username_pattern = r"^@[a-zA-Z][a-zA-Z0-9_]{4,31}$"
        if not re.match(username_pattern, cleaned):
            raise serializers.ValidationError(
                "Username группы должен содержать 5-32 символа (буквы, цифры, _). Примеры: @mygroup или -1001234567890"
            )

        return cleaned

    def validate(self, attrs):
        """
        Cross-field validation for notification settings.
        If notifications are enabled, telegram_group_id is required.
        """
        notifications_enabled = attrs.get("notifications_enabled")
        telegram_group_id = attrs.get("telegram_group_id")

        # If not in attrs, check current instance values
        if self.instance:
            if notifications_enabled is None:
                notifications_enabled = self.instance.notifications_enabled
            if "telegram_group_id" not in attrs:
                telegram_group_id = self.instance.telegram_group_id

        # Validate consistency
        if notifications_enabled and not telegram_group_id:
            raise serializers.ValidationError(
                {"telegram_group_id": "Для включения уведомлений необходимо указать ID группы Telegram"}
            )

        return attrs


class CompanyStatsSerializer(serializers.Serializer):
    """
    Serializer for company statistics.
    """

    total_companies = serializers.IntegerField()
    active_companies = serializers.IntegerField()
    inactive_companies = serializers.IntegerField()


# ============ Customer Serializers ============


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomerProfile model.
    """

    class Meta:
        model = CustomerProfile
        fields = (
            "phone_number",
            "telegram_user_id",
            "telegram_username",
            "bot_access",
            "language",
            "company",
        )
        read_only_fields = ("telegram_user_id", "telegram_username")


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer users (CustomUser with user_type='customer').
    Reads from CustomerProfile when available, falls back to legacy fields.
    """

    full_name = serializers.SerializerMethodField()
    can_use_bot = serializers.SerializerMethodField()
    orders_count = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    telegram_user_id = serializers.SerializerMethodField()
    telegram_username = serializers.SerializerMethodField()
    bot_access = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    has_profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "telegram_user_id",
            "telegram_username",
            "bot_access",
            "is_active",
            "can_use_bot",
            "has_profile",
            "company",
            "orders_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "telegram_user_id",
            "telegram_username",
            "company",
            "created_at",
            "updated_at",
        )

    def _get_profile(self, obj):
        """Get customer profile, using cached version if available."""
        if not hasattr(obj, "_cached_profile"):
            try:
                obj._cached_profile = obj.customer_profile
            except CustomerProfile.DoesNotExist:
                obj._cached_profile = None
        return obj._cached_profile

    @extend_schema_field(OpenApiTypes.STR)
    def get_full_name(self, obj):
        """Get customer's full name."""
        return obj.full_name

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_can_use_bot(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.can_use_bot
        return obj.can_use_bot

    @extend_schema_field(OpenApiTypes.STR)
    def get_phone_number(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.phone_number
        return obj.phone_number

    @extend_schema_field({"type": "integer", "nullable": True})
    def get_telegram_user_id(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.telegram_user_id
        return obj.telegram_user_id

    @extend_schema_field(OpenApiTypes.STR)
    def get_telegram_username(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.telegram_username
        return obj.telegram_username

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_bot_access(self, obj):
        profile = self._get_profile(obj)
        if profile:
            return profile.bot_access
        return obj.bot_access

    @extend_schema_field({"type": "object", "nullable": True})
    def get_company(self, obj):
        profile = self._get_profile(obj)
        company = profile.company if profile else obj.company
        if company:
            return CompanySerializer(company).data
        return None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_has_profile(self, obj):
        return self._get_profile(obj) is not None

    @extend_schema_field(OpenApiTypes.INT)
    def get_orders_count(self, obj):
        """Get count of pre-orders for this customer."""
        return obj.pre_orders.count() if hasattr(obj, "pre_orders") else 0


class CustomerCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new customer.
    Customers authenticate via Telegram only (no password needed).
    """

    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True),
        source="company",
        write_only=True,
        help_text="ID of the company this customer belongs to (required)",
    )

    class Meta:
        model = CustomUser
        fields = ("first_name", "phone_number", "company_id", "bot_access", "is_active")

    def create(self, validated_data):
        phone_number = validated_data.get("phone_number")
        validated_data["username"] = f"cust_{phone_number}" if phone_number else None
        validated_data["user_type"] = "customer"

        customer = CustomUser.objects.create(**validated_data)
        return customer


class CustomerUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating customer information.
    Customers authenticate via Telegram only (no password needed).
    """

    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True),
        source="company",
        write_only=True,
        required=False,
        help_text="ID of the company this customer belongs to",
    )

    class Meta:
        model = CustomUser
        fields = ("first_name", "phone_number", "company_id", "is_active", "bot_access")

    def validate_phone_number(self, value):
        """Validate phone_number is unique, excluding current instance."""
        instance = self.instance
        if instance and CustomUser.objects.filter(phone_number=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("Клиент с таким номером телефона уже существует.")
        return value


class CustomerLoginSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for customer login response.
    Returns customer info with nested company data.
    """

    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "company",
            "is_active",
        )
        read_only_fields = fields

    def _get_profile(self, obj):
        """Get customer profile, using cached version if available."""
        if not hasattr(obj, "_cached_profile"):
            try:
                obj._cached_profile = obj.customer_profile
            except CustomerProfile.DoesNotExist:
                obj._cached_profile = None
        return obj._cached_profile

    @extend_schema_field(OpenApiTypes.STR)
    def get_full_name(self, obj):
        """Get customer's full name."""
        return obj.full_name

    @extend_schema_field(OpenApiTypes.STR)
    def get_phone_number(self, obj):
        """Get phone number from profile first, then legacy field."""
        profile = self._get_profile(obj)
        if profile and profile.phone_number:
            return profile.phone_number
        return obj.phone_number or ""

    @extend_schema_field(CompanySerializer)
    def get_company(self, obj):
        """Get company data (id, name, slug)."""
        profile = self._get_profile(obj)
        company = None

        if profile and profile.company:
            company = profile.company
        elif hasattr(obj, "company") and obj.company:
            company = obj.company

        if company:
            return {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
            }
        return None


class CustomerStatsSerializer(serializers.Serializer):
    """
    Serializer for customer statistics.
    """

    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    customers_with_access = serializers.IntegerField()
    customers_with_telegram = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
