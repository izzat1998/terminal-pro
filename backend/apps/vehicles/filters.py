from datetime import datetime

import django_filters
from django.db.models import Q

from .models import VehicleEntry


class VehicleEntryFilter(django_filters.FilterSet):
    """
    Filters for VehicleEntry model.
    Supports filtering by both database values and Russian display names.
    """

    # Status filter - accepts both DB values and Russian names
    status = django_filters.CharFilter(method="filter_status")

    # Vehicle type filter
    vehicle_type = django_filters.CharFilter(method="filter_vehicle_type")

    # Transport type filter (for cargo vehicles)
    transport_type = django_filters.CharFilter(method="filter_transport_type")

    # Visitor type filter (for light vehicles)
    visitor_type = django_filters.CharFilter(method="filter_visitor_type")

    # Load status filters
    entry_load_status = django_filters.CharFilter(method="filter_entry_load_status")
    exit_load_status = django_filters.CharFilter(method="filter_exit_load_status")

    # Cargo type filter
    cargo_type = django_filters.CharFilter(method="filter_cargo_type")

    # Container size filter
    container_size = django_filters.CharFilter(method="filter_container_size")

    # Has exited filter
    has_exited = django_filters.BooleanFilter(method="filter_has_exited")

    # Customer filters - accepts ID directly
    customer = django_filters.NumberFilter(field_name="customer_id")
    customer_name = django_filters.CharFilter(method="filter_customer_text")

    # Destination filters
    destination_id = django_filters.NumberFilter(field_name="destination_id")
    destination = django_filters.CharFilter(method="filter_destination_text")
    destination_zone = django_filters.CharFilter(
        field_name="destination__zone", lookup_expr="iexact"
    )

    # License plate filter
    license_plate = django_filters.CharFilter(
        field_name="license_plate", lookup_expr="icontains"
    )

    # Comprehensive text search
    search_text = django_filters.CharFilter(method="filter_search_text")

    # Date filters - handles both YYYY-MM-DD and YYYY.MM.DD formats
    entry_time = django_filters.CharFilter(method="filter_entry_time")
    exit_time = django_filters.CharFilter(method="filter_exit_time")

    # Date range filters (using standard ISO format YYYY-MM-DD)
    entry_date = django_filters.DateFilter(field_name="entry_time", lookup_expr="date")
    entry_date_after = django_filters.DateFilter(
        field_name="entry_time", lookup_expr="date__gte"
    )
    entry_date_before = django_filters.DateFilter(
        field_name="entry_time", lookup_expr="date__lte"
    )

    exit_date = django_filters.DateFilter(field_name="exit_time", lookup_expr="date")
    exit_date_after = django_filters.DateFilter(
        field_name="exit_time", lookup_expr="date__gte"
    )
    exit_date_before = django_filters.DateFilter(
        field_name="exit_time", lookup_expr="date__lte"
    )

    # DateTime range filters
    entry_time_after = django_filters.DateTimeFilter(
        field_name="entry_time", lookup_expr="gte"
    )
    entry_time_before = django_filters.DateTimeFilter(
        field_name="entry_time", lookup_expr="lte"
    )
    exit_time_after = django_filters.DateTimeFilter(
        field_name="exit_time", lookup_expr="gte"
    )
    exit_time_before = django_filters.DateTimeFilter(
        field_name="exit_time", lookup_expr="lte"
    )

    # Manager filters - accepts ID directly
    manager = django_filters.NumberFilter(field_name="recorded_by_id")
    manager_name = django_filters.CharFilter(method="filter_manager_text")

    # ===== Filter Methods =====

    def filter_status(self, queryset, name, value):
        """Filter by status, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value for db_value, display in VehicleEntry.STATUS_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(status=db_value)

    def filter_vehicle_type(self, queryset, name, value):
        """Filter by vehicle type, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value for db_value, display in VehicleEntry.VEHICLE_TYPE_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(vehicle_type=db_value)

    def filter_transport_type(self, queryset, name, value):
        """Filter by transport type, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value
            for db_value, display in VehicleEntry.TRANSPORT_TYPE_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(transport_type=db_value)

    def filter_visitor_type(self, queryset, name, value):
        """Filter by visitor type, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value for db_value, display in VehicleEntry.VISITOR_TYPE_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(visitor_type=db_value)

    def filter_entry_load_status(self, queryset, name, value):
        """Filter by entry load status, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value for db_value, display in VehicleEntry.LOAD_STATUS_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(entry_load_status=db_value)

    def filter_exit_load_status(self, queryset, name, value):
        """Filter by exit load status, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value for db_value, display in VehicleEntry.LOAD_STATUS_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(exit_load_status=db_value)

    def filter_cargo_type(self, queryset, name, value):
        """Filter by cargo type, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value for db_value, display in VehicleEntry.CARGO_TYPE_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(cargo_type=db_value)

    def filter_container_size(self, queryset, name, value):
        """Filter by container size, accepting both DB values and Russian names"""
        russian_to_db = {
            display: db_value
            for db_value, display in VehicleEntry.CONTAINER_SIZE_CHOICES
        }
        db_value = russian_to_db.get(value, value)
        return queryset.filter(container_size=db_value)

    def filter_has_exited(self, queryset, name, value):
        """Filter by whether vehicle has exited (has exit_time)"""
        if value:
            return queryset.filter(exit_time__isnull=False)
        return queryset.filter(exit_time__isnull=True)

    def filter_customer_text(self, queryset, name, value):
        """
        Filter by customer name or phone (text search).
        Example: ?customer_name=Иван or ?customer_name=+998901234567
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(customer__first_name__icontains=value)
            | Q(customer__last_name__icontains=value)
            | Q(customer__phone_number__icontains=value)
        )

    def filter_destination_text(self, queryset, name, value):
        """
        Filter by destination name (text search).
        Example: ?destination=Склад
        """
        if not value:
            return queryset
        try:
            dest_id = int(value)
            return queryset.filter(destination_id=dest_id)
        except (ValueError, TypeError):
            return queryset.filter(destination__name__icontains=value)

    def filter_manager_text(self, queryset, name, value):
        """
        Filter by manager name (text search).
        Example: ?manager_name=Менеджер
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(recorded_by__first_name__icontains=value)
            | Q(recorded_by__last_name__icontains=value)
            | Q(recorded_by__username__icontains=value)
        )

    def filter_entry_time(self, queryset, name, value):
        """
        Filter by entry date. Handles both formats:
        - YYYY-MM-DD (standard ISO format)
        - YYYY.MM.DD (frontend format with dots)
        """
        if not value:
            return queryset

        # Try parsing with dots first (frontend format)
        try:
            date_obj = datetime.strptime(value, "%Y.%m.%d").date()
            return queryset.filter(entry_time__date=date_obj)
        except ValueError:
            pass

        # Try standard ISO format
        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d").date()
            return queryset.filter(entry_time__date=date_obj)
        except ValueError:
            pass

        return queryset

    def filter_exit_time(self, queryset, name, value):
        """
        Filter by exit date. Handles both formats:
        - YYYY-MM-DD (standard ISO format)
        - YYYY.MM.DD (frontend format with dots)
        """
        if not value:
            return queryset

        try:
            date_obj = datetime.strptime(value, "%Y.%m.%d").date()
            return queryset.filter(exit_time__date=date_obj)
        except ValueError:
            pass

        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d").date()
            return queryset.filter(exit_time__date=date_obj)
        except ValueError:
            pass

        return queryset

    def filter_search_text(self, queryset, name, value):
        """
        Comprehensive search across all relevant text fields.
        Searches: license_plate, customer name/phone, manager name, destination
        """
        return queryset.filter(
            Q(license_plate__icontains=value)
            | Q(customer__first_name__icontains=value)
            | Q(customer__last_name__icontains=value)
            | Q(customer__phone_number__icontains=value)
            | Q(recorded_by__first_name__icontains=value)
            | Q(recorded_by__last_name__icontains=value)
            | Q(recorded_by__username__icontains=value)
            | Q(destination__name__icontains=value)
            | Q(destination__zone__icontains=value)
        )

    class Meta:
        model = VehicleEntry
        fields = []
