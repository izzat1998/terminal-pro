"""
Utility functions for Telegram bot handlers
"""


def format_container_number(container_number: str) -> str:
    """
    Format container number with prefix and postfix separated.

    Container numbers follow ISO format: 4 letters (prefix) + 7 digits (postfix)
    Example: HDMU6565958 -> HDMU | 6565958

    Args:
        container_number: Full container number (11 characters)

    Returns:
        Formatted string with prefix and postfix separated by ' | '
    """
    if not container_number or len(container_number) != 11:
        return container_number

    prefix = container_number[:4]   # First 4 letters (owner code)
    postfix = container_number[4:]  # Last 7 digits (serial + check digit)

    return f"{prefix} | {postfix}"
