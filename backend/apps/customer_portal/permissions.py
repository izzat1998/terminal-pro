"""
Permission classes for customer portal API endpoints.

These permissions ensure customers can only access their own data and
their company's resources.
"""

from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    """
    Permission class that allows access only to authenticated customer users.
    """

    def has_permission(self, request, view):
        """
        Check if user is authenticated and has customer user_type.
        """
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "user_type")
            and request.user.user_type == "customer"
        )


class IsCustomerOwner(BasePermission):
    """
    Permission class that allows customers to access only their own resources.
    Used for PreOrder detail views to ensure customers can only access their own pre-orders.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if the object belongs to the requesting customer.
        """
        return hasattr(obj, "customer") and obj.customer == request.user


class HasCompanyAccess(BasePermission):
    """
    Permission class that allows customers to access only their company's resources.
    Used for ContainerEntry detail views to ensure customers only see their company's data.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if the object belongs to the requesting customer's company.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get customer's company
        customer_company = None
        try:
            # Try to get company from profile first
            customer_company = request.user.customer_profile.company
        except Exception:
            # Fallback to legacy company field if profile doesn't exist
            if hasattr(request.user, "company"):
                customer_company = request.user.company

        if not customer_company:
            return False

        # Check if object has company field and matches customer's company
        if hasattr(obj, "company"):
            return obj.company == customer_company

        return False
