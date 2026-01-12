"""
Service for automatic license plate recognition via PlateRecognizer.com API
"""

import json
import logging
import os
from dataclasses import dataclass

import aiohttp

from apps.core.services.base_service import BaseService


# Use Python's logging instead of importing from bot.py to avoid circular imports
logger = logging.getLogger(__name__)


@dataclass
class PlateRecognitionResult:
    """Data class for plate recognition results"""

    plate_number: str
    confidence: float
    success: bool
    error_message: str | None = None


class PlateRecognizerService(BaseService):
    """
    Service for automatic license plate recognition via PlateRecognizer.com API

    Documentation: https://docs.platerecognizer.com/
    """

    API_URL = "https://api.platerecognizer.com/v1/plate-reader/"

    def __init__(self):
        super().__init__()  # Initialize BaseService for logging
        self.api_key = os.getenv("PLATE_RECOGNIZER_API_KEY")
        if not self.api_key:
            self.logger.warning(
                "PLATE_RECOGNIZER_API_KEY not set - plate recognition disabled"
            )

    async def recognize_plate(
        self, photo_bytes: bytes, region: str = "uz"
    ) -> PlateRecognitionResult:
        """
        Recognize license plate from photo bytes

        Args:
            photo_bytes: Image file bytes
            region: Region code for recognition (default: 'uz' for Uzbekistan)

        Returns:
            PlateRecognitionResult with plate number, confidence, and success status
        """
        if not self.api_key:
            self.logger.error("API key not configured")
            return PlateRecognitionResult(
                plate_number="",
                confidence=0.0,
                success=False,
                error_message="API key not configured",
            )

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Token {self.api_key}"}
                data = aiohttp.FormData()
                data.add_field(
                    "upload",
                    photo_bytes,
                    filename="plate.jpg",
                    content_type="image/jpeg",
                )
                data.add_field("regions", region)

                async with session.post(
                    self.API_URL,
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status not in (200, 201):
                        error_text = await response.text()
                        self.logger.error(
                            f"API error: {response.status} - {error_text}"
                        )

                        # Try to parse JSON error for better message
                        error_msg = f"API error: {response.status}"
                        try:
                            error_json = json.loads(error_text)
                            if "detail" in error_json:
                                error_msg = f"API error: {error_json['detail']}"
                        except (json.JSONDecodeError, KeyError):
                            pass

                        return PlateRecognitionResult(
                            plate_number="",
                            confidence=0.0,
                            success=False,
                            error_message=error_msg,
                        )

                    result = await response.json()

                    # Debug: Log raw API response
                    self.logger.info(f"PlateRecognizer raw response: {result}")

                    # Extract best match
                    if result.get("results") and len(result["results"]) > 0:
                        best_result = result["results"][0]
                        plate = best_result.get("plate", "").strip().upper()
                        confidence = best_result.get("score", 0.0)

                        logger.info(
                            f"Detected plate: {plate} (confidence: {confidence:.2%})"
                        )

                        # Lenient validation - accept any non-empty plate
                        if plate:
                            return PlateRecognitionResult(
                                plate_number=plate,
                                confidence=confidence,
                                success=True,
                                error_message=None,
                            )
                        else:
                            logger.warning("API returned empty plate string")
                            return PlateRecognitionResult(
                                plate_number="",
                                confidence=0.0,
                                success=False,
                                error_message="Empty plate detected",
                            )
                    else:
                        logger.warning("No plates detected in image")
                        return PlateRecognitionResult(
                            plate_number="",
                            confidence=0.0,
                            success=False,
                            error_message="No plates detected",
                        )

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP error during plate recognition: {e!s}")
            return PlateRecognitionResult(
                plate_number="",
                confidence=0.0,
                success=False,
                error_message="Network error",
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error during plate recognition: {e!s}", exc_info=True
            )
            return PlateRecognitionResult(
                plate_number="",
                confidence=0.0,
                success=False,
                error_message="Unexpected error",
            )

    def format_plate_number(self, plate: str) -> str:
        """
        Basic formatting for plate number (lenient - no strict validation)

        Args:
            plate: Raw plate number string

        Returns:
            Formatted plate number (uppercase, trimmed)
        """
        return plate.strip().upper()
