"""
Utility functions for Telegram bot handlers
"""


def format_container_number(container_number: str) -> str:
    """
    Format container number for display.

    Container numbers follow ISO format: 4 letters (prefix) + 7 digits (postfix)
    Example: HDMU6565958 -> HDMU6565958

    Args:
        container_number: Full container number (11 characters)

    Returns:
        Container number as-is (no separators)
    """
    return container_number or ""
