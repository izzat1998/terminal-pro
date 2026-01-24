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


@dataclass
class VehicleDetectionResult:
    """
    Enhanced detection result with vehicle type classification.

    Used by gate camera integration to get both plate number and vehicle type.
    """

    success: bool
    plate_number: str
    plate_confidence: float
    vehicle_type: str  # "TRUCK" | "CAR" | "WAGON" | "UNKNOWN"
    vehicle_type_confidence: float
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_color: Optional[str] = None
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

    def detect_vehicle(
        self, image_bytes: bytes, region: str = "uz"
    ) -> VehicleDetectionResult:
        """
        Detect vehicle and recognize license plate from image bytes.

        Enhanced version that extracts both plate number AND vehicle type/details.
        Use this method for gate camera integration where vehicle classification is needed.

        Args:
            image_bytes: Raw image data
            region: Country code for plate format (default: "uz")

        Returns:
            VehicleDetectionResult with plate number, vehicle type, and additional details
        """
        try:
            from telegram_bot.services.plate_recognizer_service import (
                PlateRecognizerService,
            )

            plate_service = PlateRecognizerService()
            result = async_to_sync(plate_service.detect_vehicle)(
                photo_bytes=image_bytes, region=region
            )

            return VehicleDetectionResult(
                success=result.success,
                plate_number=result.plate_number,
                plate_confidence=result.plate_confidence,
                vehicle_type=result.vehicle_type,
                vehicle_type_confidence=result.vehicle_type_confidence,
                vehicle_make=result.vehicle_make,
                vehicle_model=result.vehicle_model,
                vehicle_color=result.vehicle_color,
                error_message=result.error_message,
            )

        except ImportError as e:
            self.logger.error(f"PlateRecognizer service unavailable: {e}")
            return VehicleDetectionResult(
                success=False,
                plate_number="",
                plate_confidence=0.0,
                vehicle_type="UNKNOWN",
                vehicle_type_confidence=0.0,
                error_message="Plate recognizer service not available",
            )
        except Exception as e:
            self.logger.error(f"Vehicle detection failed: {e}")
            return VehicleDetectionResult(
                success=False,
                plate_number="",
                plate_confidence=0.0,
                vehicle_type="UNKNOWN",
                vehicle_type_confidence=0.0,
                error_message="Unexpected error occurred",
            )
