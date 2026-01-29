"""Shared utility helpers for the MTT backend."""


def safe_int_param(value, default, *, min_val=None, max_val=None):
    """
    Parse a query-parameter value to int, returning *default* on bad input.

    Optionally clamp the result to [min_val, max_val].
    """
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default

    if min_val is not None:
        result = max(result, min_val)
    if max_val is not None:
        result = min(result, max_val)
    return result
