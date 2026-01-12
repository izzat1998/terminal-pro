from datetime import datetime

import django_filters
from django.db.models import Q

from .models import ContainerEntry


class ContainerEntryFilter(django_filters.FilterSet):
    """
    Filters for ContainerEntry model
    Supports filtering by both database values (EMPTY, LADEN, TRUCK, WAGON)
    and Russian display names (Порожний, Гружёный, Авто, Вагон)
    """

    # Custom method filters that accept both DB values and Russian names
    status = django_filters.CharFilter(method="filter_status")
    transport_type = django_filters.CharFilter(method="filter_transport_type")
    exit_transport_type = django_filters.CharFilter(method="filter_exit_transport_type")
    has_exited = django_filters.BooleanFilter(method="filter_has_exited")

    # Container owner filters
    # Support both ID-based and text search for frontend compatibility
    container_owner_id = django_filters.CharFilter(method="filter_container_owner_ids")
    container_owner_ids = django_filters.CharFilter(method="filter_container_owner_ids")
    # Text search by owner name (this is what frontend sends as 'container_owner')
    container_owner = django_filters.CharFilter(method="filter_container_owner_text")

    # Comprehensive text search filter
    search_text = django_filters.CharFilter(method="filter_search_text")

    # Custom date filters that handle YYYY.MM.DD format (with dots)
    entry_time = django_filters.CharFilter(method="filter_entry_time")
    exit_date = django_filters.CharFilter(method="filter_exit_date_custom")
    additional_crane_operation_date = django_filters.CharFilter(method="filter_crane_operation_date")

    # Numeric range filters
    cargo_weight_min = django_filters.NumberFilter(field_name="cargo_weight", lookup_expr="gte")
    cargo_weight_max = django_filters.NumberFilter(field_name="cargo_weight", lookup_expr="lte")
    cargo_weight_range = django_filters.CharFilter(method="filter_cargo_weight_range")

    dwell_time_min = django_filters.NumberFilter(field_name="dwell_time_days", lookup_expr="gte")
    dwell_time_max = django_filters.NumberFilter(field_name="dwell_time_days", lookup_expr="lte")
    dwell_time_range = django_filters.CharFilter(method="filter_dwell_time_range")

    # Combined datetime filters
    entry_time_after = django_filters.DateTimeFilter(field_name="entry_time", lookup_expr="gte")
    entry_time_before = django_filters.DateTimeFilter(field_name="entry_time", lookup_expr="lte")

    exit_time_after = django_filters.DateTimeFilter(field_name="exit_date", lookup_expr="gte")
    exit_time_before = django_filters.DateTimeFilter(field_name="exit_date", lookup_expr="lte")

    def filter_status(self, queryset, name, value):
        """
        Filter by status, accepting both DB values and Russian names.
        Handles data inconsistency where both formats may exist in database.
        """
        # Define value pairs (Russian display, English DB value)
        status_pairs = {
            "Гружёный": ["LADEN", "Гружёный"],
            "LADEN": ["LADEN", "Гружёный"],
            "Порожний": ["EMPTY", "Порожний"],
            "EMPTY": ["EMPTY", "Порожний"],
        }
        # Get both possible values for this status
        values_to_match = status_pairs.get(value, [value])
        return queryset.filter(status__in=values_to_match)

    def filter_transport_type(self, queryset, name, value):
        """Filter by transport type, accepting both DB values and Russian names"""
        # Mapping: Russian name -> database value
        russian_to_db = {display: db_value for db_value, display in ContainerEntry.TRANSPORT_CHOICES}
        db_value = russian_to_db.get(value, value)
        return queryset.filter(transport_type=db_value)

    def filter_exit_transport_type(self, queryset, name, value):
        """Filter by exit transport type, accepting both DB values and Russian names"""
        # Mapping: Russian name -> database value
        russian_to_db = {display: db_value for db_value, display in ContainerEntry.EXIT_TRANSPORT_CHOICES}
        db_value = russian_to_db.get(value, value)
        return queryset.filter(exit_transport_type=db_value)

    def filter_has_exited(self, queryset, name, value):
        """Filter by whether container has exited (has exit_date)"""
        if value:
            return queryset.filter(exit_date__isnull=False)
        return queryset.filter(exit_date__isnull=True)

    def filter_container_owner_ids(self, queryset, name, value):
        """
        Filter by container owner IDs. Accepts comma-separated list of IDs.
        Example: ?container_owner_ids=1,2,3
        """
        if not value:
            return queryset
        try:
            # Split comma-separated values and convert to integers
            owner_ids = [int(id_str.strip()) for id_str in value.split(",") if id_str.strip()]
            if owner_ids:
                return queryset.filter(container_owner_id__in=owner_ids)
        except (ValueError, TypeError):
            # If conversion fails, return empty queryset
            pass
        return queryset

    def filter_container_owner_text(self, queryset, name, value):
        """
        Filter by container owner name (text search).
        Frontend sends this as 'container_owner' parameter with text value.
        Example: ?container_owner=SomeOwnerName
        """
        if not value:
            return queryset
        # Try to parse as integer first (for backward compatibility with ID-based search)
        try:
            owner_id = int(value)
            return queryset.filter(container_owner_id=owner_id)
        except (ValueError, TypeError):
            # If not a number, search by owner name (partial match)
            return queryset.filter(container_owner__name__icontains=value)

    def filter_company_ids(self, queryset, name, value):
        """
        Filter by company IDs. Accepts comma-separated list.
        Example: ?company_ids=1,2,3
        """
        if not value:
            return queryset
        try:
            company_ids = [int(id_str.strip()) for id_str in value.split(",") if id_str.strip()]
            if company_ids:
                return queryset.filter(company_id__in=company_ids)
        except (ValueError, TypeError):
            pass
        return queryset

    def filter_company_slug(self, queryset, name, value):
        """
        Filter by company slug.
        Example: ?company_slug=my-company
        """
        if not value:
            return queryset
        return queryset.filter(company__slug=value)

    def filter_company_text(self, queryset, name, value):
        """
        Filter by company name (text search, partial match).
        Example: ?company_name=SomeCompany
        """
        if not value:
            return queryset
        # Try ID first for backward compatibility
        try:
            company_id = int(value)
            return queryset.filter(company_id=company_id)
        except (ValueError, TypeError):
            # Search by company name (partial match)
            return queryset.filter(company__name__icontains=value)

    def filter_entry_time(self, queryset, name, value):
        """
        Filter by entry date. Handles both formats:
        - YYYY-MM-DD (standard ISO format)
        - YYYY.MM.DD (frontend format with dots)
        Example: ?entry_time=2025.11.10
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

        # If both fail, return unfiltered queryset
        return queryset

    def filter_exit_date_custom(self, queryset, name, value):
        """
        Filter by exit date. Handles both formats:
        - YYYY-MM-DD (standard ISO format)
        - YYYY.MM.DD (frontend format with dots)
        Example: ?exit_date=2025.11.10
        """
        if not value:
            return queryset

        # Try parsing with dots first (frontend format)
        try:
            date_obj = datetime.strptime(value, "%Y.%m.%d").date()
            return queryset.filter(exit_date__date=date_obj)
        except ValueError:
            pass

        # Try standard ISO format
        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d").date()
            return queryset.filter(exit_date__date=date_obj)
        except ValueError:
            pass

        # If both fail, return unfiltered queryset
        return queryset

    def filter_crane_operation_date(self, queryset, name, value):
        """
        Filter by additional crane operation date. Handles both formats:
        - YYYY-MM-DD (standard ISO format)
        - YYYY.MM.DD (frontend format with dots)
        Example: ?additional_crane_operation_date=2025.11.10
        """
        if not value:
            return queryset

        # Try parsing with dots first (frontend format)
        try:
            date_obj = datetime.strptime(value, "%Y.%m.%d").date()
            return queryset.filter(crane_operations__operation_date__date=date_obj).distinct()
        except ValueError:
            pass

        # Try standard ISO format
        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d").date()
            return queryset.filter(crane_operations__operation_date__date=date_obj).distinct()
        except ValueError:
            pass

        # If both fail, return unfiltered queryset
        return queryset

    container_number = django_filters.CharFilter(field_name="container__container_number", lookup_expr="iexact")

    # Date range filters (using standard ISO format YYYY-MM-DD)
    entry_date = django_filters.DateFilter(field_name="entry_time", lookup_expr="date")
    entry_date_after = django_filters.DateFilter(field_name="entry_time", lookup_expr="date__gte")
    entry_date_before = django_filters.DateFilter(field_name="entry_time", lookup_expr="date__lte")

    # Exit date range filters (using standard ISO format YYYY-MM-DD)
    # Note: exit_date exact match handled by filter_exit_date_custom() above for YYYY.MM.DD format
    exit_date_after = django_filters.DateFilter(field_name="exit_date", lookup_expr="date__gte")
    exit_date_before = django_filters.DateFilter(field_name="exit_date", lookup_expr="date__lte")

    # Container filters
    container_iso_type = django_filters.CharFilter(field_name="container__iso_type", lookup_expr="exact")

    # Text search filters - explicit definitions for frontend compatibility
    # These use icontains by default for partial matching
    client_name = django_filters.CharFilter(field_name="client_name", lookup_expr="icontains")
    # Company filters (parallel to container_owner filters)
    company_id = django_filters.CharFilter(method="filter_company_ids")
    company_ids = django_filters.CharFilter(method="filter_company_ids")
    company_slug = django_filters.CharFilter(method="filter_company_slug")
    company_name = django_filters.CharFilter(method="filter_company_text")
    cargo_name = django_filters.CharFilter(field_name="cargo_name", lookup_expr="icontains")
    entry_train_number = django_filters.CharFilter(field_name="entry_train_number", lookup_expr="icontains")
    transport_number = django_filters.CharFilter(field_name="transport_number", lookup_expr="icontains")
    exit_train_number = django_filters.CharFilter(field_name="exit_train_number", lookup_expr="icontains")
    exit_transport_number = django_filters.CharFilter(field_name="exit_transport_number", lookup_expr="icontains")
    destination_station = django_filters.CharFilter(field_name="destination_station", lookup_expr="icontains")
    location = django_filters.CharFilter(field_name="location", lookup_expr="icontains")
    note = django_filters.CharFilter(field_name="note", lookup_expr="icontains")
    cargo_weight = django_filters.NumberFilter(field_name="cargo_weight", lookup_expr="exact")

    # User filters
    recorded_by_username = django_filters.CharFilter(field_name="recorded_by__username", lookup_expr="iexact")
    recorded_by_email = django_filters.CharFilter(field_name="recorded_by__email", lookup_expr="icontains")

    def filter_search_text(self, queryset, name, value):
        """
        Comprehensive search across all relevant text fields
        Searches: container number, client, owner, cargo, location, notes, train numbers, stations
        """
        return queryset.filter(
            Q(container__container_number__icontains=value)
            | Q(client_name__icontains=value)
            | Q(company__name__icontains=value)
            | Q(container_owner__name__icontains=value)
            | Q(cargo_name__icontains=value)
            | Q(location__icontains=value)
            | Q(note__icontains=value)
            | Q(transport_number__icontains=value)
            | Q(entry_train_number__icontains=value)
            | Q(exit_train_number__icontains=value)
            | Q(exit_transport_number__icontains=value)
            | Q(destination_station__icontains=value)
            | Q(recorded_by__username__icontains=value)
            | Q(recorded_by__email__icontains=value)
            | Q(recorded_by__first_name__icontains=value)
            | Q(recorded_by__last_name__icontains=value)
        )

    def filter_cargo_weight_range(self, queryset, name, value):
        """
        Filter by cargo weight range. Accepts format: 'min-max'
        Example: '100-500' filters cargo_weight between 100 and 500
        """
        if not value:
            return queryset
        try:
            parts = value.split("-")
            if len(parts) == 2:
                min_weight = float(parts[0])
                max_weight = float(parts[1])
                return queryset.filter(cargo_weight__gte=min_weight, cargo_weight__lte=max_weight)
        except (ValueError, IndexError):
            pass
        return queryset

    def filter_dwell_time_range(self, queryset, name, value):
        """
        Filter by dwell time range (days). Accepts format: 'min-max'
        Example: '1-10' filters dwell_time_days between 1 and 10
        """
        if not value:
            return queryset
        try:
            parts = value.split("-")
            if len(parts) == 2:
                min_days = int(parts[0])
                max_days = int(parts[1])
                return queryset.filter(dwell_time_days__gte=min_days, dwell_time_days__lte=max_days)
        except (ValueError, IndexError):
            pass
        return queryset

    class Meta:
        model = ContainerEntry
        # All filters are explicitly defined above for better control and frontend compatibility
        fields = []
