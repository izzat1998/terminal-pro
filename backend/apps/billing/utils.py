"""Shared utility helpers for the billing app."""


def filter_storage_cost_entries(entries, params):
    """
    Apply common storage cost filters to a ContainerEntry queryset.

    Args:
        entries: ContainerEntry queryset (already filtered by company)
        params: dict-like object (e.g. request.query_params) with optional keys:
            - status: 'active' or 'exited'
            - search: container number substring
            - entry_date_from: YYYY-MM-DD
            - entry_date_to: YYYY-MM-DD

    Returns:
        Filtered queryset ordered by -entry_time
    """
    status_filter = params.get("status")
    if status_filter == "active":
        entries = entries.filter(exit_date__isnull=True)
    elif status_filter == "exited":
        entries = entries.filter(exit_date__isnull=False)

    search = params.get("search", "")
    if hasattr(search, "strip"):
        search = search.strip()
    if search:
        entries = entries.filter(container__container_number__icontains=search)

    entry_date_from = params.get("entry_date_from")
    if entry_date_from:
        entries = entries.filter(entry_time__date__gte=entry_date_from)

    entry_date_to = params.get("entry_date_to")
    if entry_date_to:
        entries = entries.filter(entry_time__date__lte=entry_date_to)

    return entries.order_by("-entry_time")
