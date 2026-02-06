"""
Service for fetching and caching exchange rates from the Central Bank of Uzbekistan.

API: https://cbu.uz/ru/arkhiv-kursov-valyut/json/{ccy}/{YYYY-MM-DD}/
Public, free, no authentication required.
"""

import calendar
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from django.utils import timezone

from apps.billing.models import ExchangeRate

logger = logging.getLogger(__name__)

CBU_API_URL = "https://cbu.uz/ru/arkhiv-kursov-valyut/json/{ccy}/{date}/"
REQUEST_TIMEOUT = 10  # seconds


class CBUServiceError(Exception):
    """Raised when CBU API call fails."""


def get_rate(target_date: date, currency: str = "USD") -> Decimal:
    """
    Get the exchange rate for a given date.

    Checks the local cache first. If not found, fetches from cbu.uz and caches.
    Returns the rate as Decimal.
    """
    cached = ExchangeRate.objects.filter(
        currency=currency, date=target_date
    ).first()

    if cached:
        return cached.rate

    return fetch_and_cache(target_date, currency)


def fetch_and_cache(target_date: date, currency: str = "USD") -> Decimal:
    """
    Fetch rate from CBU API and store in cache.

    Raises CBUServiceError if the API is unreachable or returns unexpected data.
    """
    url = CBU_API_URL.format(
        ccy=currency,
        date=target_date.strftime("%Y-%m-%d"),
    )

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("CBU API request failed: %s", exc)
        raise CBUServiceError(
            f"Не удалось получить курс ЦБ за {target_date}"
        ) from exc

    data = response.json()
    if not data or not isinstance(data, list):
        raise CBUServiceError(
            f"ЦБ не вернул данные за {target_date} ({currency})"
        )

    raw_rate = data[0].get("Rate")
    if raw_rate is None:
        raise CBUServiceError(
            f"В ответе ЦБ отсутствует поле Rate за {target_date}"
        )

    try:
        rate = Decimal(str(raw_rate))
    except (InvalidOperation, ValueError) as exc:
        raise CBUServiceError(
            f"Некорректное значение курса: {raw_rate}"
        ) from exc

    # Upsert into cache
    ExchangeRate.objects.update_or_create(
        currency=currency,
        date=target_date,
        defaults={
            "rate": rate,
            "fetched_at": timezone.now(),
        },
    )

    logger.info(
        "Cached CBU rate: %s %s = %s UZS",
        currency,
        target_date,
        rate,
    )
    return rate


def get_last_day_of_month_rate(year: int, month: int, currency: str = "USD") -> Decimal:
    """
    Convenience: get the rate for the last day of a given month.

    This is what accountants typically need for monthly billing documents.
    """
    last_day = calendar.monthrange(year, month)[1]
    target = date(year, month, last_day)
    return get_rate(target, currency)
