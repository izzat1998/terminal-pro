from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from apps.core.admin import TimestampedModelAdmin

from .models import Company, CustomerProfile, CustomUser, ManagerProfile


class ManagerProfileInline(admin.StackedInline):
    """Inline admin for ManagerProfile."""

    model = ManagerProfile
    can_delete = False
    verbose_name = "Manager Profile"
    verbose_name_plural = "Manager Profile"
    extra = 0
    max_num = 1
    fields = (
        "phone_number",
        "telegram_user_id",
        "telegram_username",
        "bot_access",
        "gate_access",
        "language",
        "company",
    )
    readonly_fields = ("telegram_user_id", "telegram_username")


class CustomerProfileInline(admin.StackedInline):
    """Inline admin for CustomerProfile."""

    model = CustomerProfile
    can_delete = False
    verbose_name = "Customer Profile"
    verbose_name_plural = "Customer Profile"
    extra = 0
    max_num = 1
    fields = (
        "phone_number",
        "telegram_user_id",
        "telegram_username",
        "bot_access",
        "language",
        "company",
    )
    readonly_fields = ("telegram_user_id", "telegram_username")


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin, TimestampedModelAdmin):
    """
    Unified admin interface for both API users and Telegram bot managers/customers.
    Shows appropriate profile inline based on user_type.
    """

    def get_inlines(self, request, obj=None):
        """Show appropriate profile inline based on user_type."""
        if obj is None:
            return []
        if obj.user_type == "manager":
            return [ManagerProfileInline]
        elif obj.user_type == "customer":
            return [CustomerProfileInline]
        return []

    def get_list_display(self, request):
        """Show different fields based on user type"""
        return (
            "id",
            "username",
            "email",
            "first_name",
            "user_type",
            "telegram_info",
            "access_status",
            "is_active",
            "created_at",
        )

    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "user_type",
        "is_active",
        "created_at",
    )

    list_filter = (
        "user_type",
        "is_admin",
        "is_staff",
        "is_active",
        "bot_access",
        "gate_access",
        ("telegram_user_id", admin.EmptyFieldListFilter),
        "date_joined",
        "created_at",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "telegram_username",
    )

    readonly_fields = ("created_at", "updated_at", "telegram_info", "access_status")

    fieldsets = (
        ("Account Type", {"fields": ("user_type",)}),
        (
            "API User Fields (for API users)",
            {
                "fields": ("username", "email", "is_admin", "is_staff"),
                "description": 'Used when user_type = "admin"',
            },
        ),
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "phone_number")},
        ),
        (
            "Authentication",
            {
                "fields": ("password",),
                "description": "Password will be hashed automatically. Leave blank to keep current password.",
            },
        ),
        (
            "Telegram Integration",
            {
                "fields": ("telegram_user_id", "telegram_username", "telegram_info"),
                "description": "Automatically filled when manager shares phone in bot",
                "classes": ("collapse",),
            },
        ),
        (
            "Manager Access Control",
            {
                "fields": ("bot_access", "gate_access", "access_status"),
                "description": 'Used when user_type = "manager"',
                "classes": ("collapse",),
            },
        ),
        (
            "Permissions",
            {
                "fields": ("is_active", "groups", "user_permissions"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    actions = [
        "grant_manager_access",
        "revoke_manager_access",
        "mark_as_api_user",
        "mark_as_manager",
    ]

    def save_model(self, request, obj, form, change):
        """Handle password hashing when saving user."""
        # Only hash password if it was actually changed (not already hashed)
        password = form.cleaned_data.get("password")
        if password and not password.startswith("pbkdf2_sha256$"):
            obj.set_password(password)
        super().save_model(request, obj, form, change)

    def telegram_info(self, obj):
        """Display Telegram connection status (profile first, then legacy)."""
        if obj.user_type not in ("manager", "customer"):
            return "—"

        # Get telegram info from profile first, then legacy
        profile = obj.get_profile()
        telegram_user_id = profile.telegram_user_id if profile else obj.telegram_user_id
        telegram_username = profile.telegram_username if profile else obj.telegram_username

        if telegram_user_id:
            username_str = f"@{telegram_username}" if telegram_username else "No username"
            return format_html(
                '✅ <span style="color: green;">Linked</span><br><small>{}<br>ID: {}</small>',
                username_str,
                telegram_user_id,
            )
        return format_html('<span style="color: gray;">❌ Not linked</span>')

    telegram_info.short_description = "Telegram"

    def access_status(self, obj):
        """Display access status with visual indicator (profile first, then legacy)."""
        if obj.user_type not in ("manager", "customer"):
            return "—"
        if not obj.is_active:
            return format_html('<span style="color: red;">🔴 Deactivated</span>')

        # Get bot_access from profile first, then legacy
        profile = obj.get_profile()
        bot_access = profile.bot_access if profile else obj.bot_access

        if bot_access:
            return format_html('<span style="color: green;">✅ Has Access</span>')
        return format_html('<span style="color: red;">❌ No Access</span>')

    access_status.short_description = "Status"

    def grant_manager_access(self, request, queryset):
        """Bulk action to grant bot access to selected managers (dual-write)."""
        managers = queryset.filter(user_type="manager")
        count = 0
        for manager in managers:
            # Update legacy field
            if not manager.bot_access:
                manager.bot_access = True
                manager.save(update_fields=["bot_access"])
                count += 1
            # Update profile if exists
            try:
                profile = manager.manager_profile
                if not profile.bot_access:
                    profile.bot_access = True
                    profile.save(update_fields=["bot_access"])
            except ManagerProfile.DoesNotExist:
                pass

        self.message_user(
            request,
            f"Successfully granted access to {count} manager(s).",
            level="success",
        )

    grant_manager_access.short_description = "✅ Grant bot access to managers"

    def revoke_manager_access(self, request, queryset):
        """Bulk action to revoke bot access from selected managers (dual-write)."""
        managers = queryset.filter(user_type="manager")
        count = 0
        for manager in managers:
            # Update legacy field
            if manager.bot_access:
                manager.bot_access = False
                manager.save(update_fields=["bot_access"])
                count += 1
            # Update profile if exists
            try:
                profile = manager.manager_profile
                if profile.bot_access:
                    profile.bot_access = False
                    profile.save(update_fields=["bot_access"])
            except ManagerProfile.DoesNotExist:
                pass

        self.message_user(
            request,
            f"Successfully revoked access from {count} manager(s).",
            level="success",
        )

    revoke_manager_access.short_description = "❌ Revoke bot access from managers"

    def mark_as_api_user(self, request, queryset):
        """Mark selected users as API users."""
        count = queryset.update(user_type="admin")
        self.message_user(request, f"Marked {count} user(s) as API users.", level="success")

    mark_as_api_user.short_description = "Mark as API User"

    def mark_as_manager(self, request, queryset):
        """Mark selected users as managers."""
        count = queryset.update(user_type="manager")
        self.message_user(request, f"Marked {count} user(s) as managers.", level="success")

    mark_as_manager.short_description = "Mark as Manager"


@admin.register(ManagerProfile)
class ManagerProfileAdmin(TimestampedModelAdmin):
    """Admin interface for ManagerProfile."""

    list_display = (
        "user",
        "phone_number",
        "bot_access",
        "gate_access",
        "telegram_status",
        "company",
        "created_at",
    )
    list_filter = ("bot_access", "gate_access", "language", "company")
    search_fields = ("user__first_name", "phone_number", "telegram_username")
    readonly_fields = ("telegram_user_id", "telegram_username", "created_at", "updated_at")
    raw_id_fields = ("user",)

    def telegram_status(self, obj):
        """Display Telegram connection status."""
        if obj.telegram_user_id:
            return format_html('<span style="color: green;">✅ Linked</span>')
        return format_html('<span style="color: gray;">❌ Not linked</span>')

    telegram_status.short_description = "Telegram"


@admin.register(CustomerProfile)
class CustomerProfileAdmin(TimestampedModelAdmin):
    """Admin interface for CustomerProfile."""

    list_display = (
        "user",
        "phone_number",
        "bot_access",
        "telegram_status",
        "company",
        "created_at",
    )
    list_filter = ("bot_access", "language", "company")
    search_fields = ("user__first_name", "phone_number", "telegram_username")
    readonly_fields = ("telegram_user_id", "telegram_username", "created_at", "updated_at")
    raw_id_fields = ("user",)

    def telegram_status(self, obj):
        """Display Telegram connection status."""
        if obj.telegram_user_id:
            return format_html('<span style="color: green;">✅ Linked</span>')
        return format_html('<span style="color: gray;">❌ Not linked</span>')

    telegram_status.short_description = "Telegram"


@admin.register(Company)
class CompanyAdmin(TimestampedModelAdmin):
    """Admin interface for Company."""

    list_display = (
        "id",
        "name",
        "slug",
        "is_active",
        "notifications_enabled",
        "telegram_group_name",
        "manager_count",
        "customer_count",
        "created_at",
    )
    list_filter = ("is_active", "notifications_enabled")
    search_fields = ("name", "slug", "telegram_group_name")
    readonly_fields = ("slug", "created_at", "updated_at")
    prepopulated_fields = {}  # Slug is auto-generated from name

    fieldsets = (
        (None, {"fields": ("name", "slug", "is_active")}),
        (
            "Telegram Notifications",
            {
                "fields": (
                    "notifications_enabled",
                    "telegram_group_id",
                    "telegram_group_name",
                ),
                "description": "Configure Telegram group notifications for this company",
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def manager_count(self, obj):
        """Count managers linked via profiles."""
        return ManagerProfile.objects.filter(company=obj).count()

    manager_count.short_description = "Managers"

    def customer_count(self, obj):
        """Count customers linked via profiles."""
        return CustomerProfile.objects.filter(company=obj).count()

    customer_count.short_description = "Customers"
