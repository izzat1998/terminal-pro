"""
Shared plate recognition service wrapper for synchronous Django views.
Wraps the async telegram_bot service for use in REST API endpoints.
"""

from dataclasses import dataclass
from typing import Optional

from asgiref.sync import async_to_sync

from apps.core.services.base_service import BaseService


@dataclass
class PlateRecognitionResult:
    """Result of plate recognition operation."""

    success: bool
    plate_number: str
    confidence: float
    error_message: Optional[str] = None


class PlateRecognizerAPIService(BaseService):
    """
    Synchronous wrapper for the async PlateRecognizerService.
    Used by REST API views to perform plate recognition.
    """

    def recognize_plate(
        self, image_bytes: bytes, region: str = "uz"
    ) -> PlateRecognitionResult:
        """
        Recognize license plate from image bytes.

        Args:
            image_bytes: Raw image data
            region: Country code for plate format (default: "uz")

        Returns:
            PlateRecognitionResult with success status and plate data
        """
        try:
            from telegram_bot.services.plate_recognizer_service import (
                PlateRecognizerService,
            )

            plate_service = PlateRecognizerService()
            result = async_to_sync(plate_service.recognize_plate)(
                photo_bytes=image_bytes, region=region
            )

            return PlateRecognitionResult(
                success=result.success,
                plate_number=result.plate_number if result.success else "",
                confidence=result.confidence if result.success else 0.0,
                error_message=result.error_message,
            )

        except ImportError as e:
            self.logger.error(f"PlateRecognizer service unavailable: {e}")
            return PlateRecognitionResult(
                success=False,
                plate_number="",
                confidence=0.0,
                error_message="Plate recognizer service not available",
            )
        except Exception as e:
            self.logger.error(f"Plate recognition failed: {e}")
            return PlateRecognitionResult(
                success=False,
                plate_number="",
                confidence=0.0,
                error_message="Unexpected error occurred",
            )
