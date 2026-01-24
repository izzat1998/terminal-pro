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
    """Data class for plate recognition results (legacy, use VehicleDetectionResult for new code)"""

    plate_number: str
    confidence: float
    success: bool
    error_message: str | None = None


@dataclass
class VehicleDetectionResult:
    """
    Enhanced detection result with vehicle type classification.

    PlateRecognizer API returns vehicle data including type, make, model, and color.
    This dataclass captures the full detection result for gate camera integration.
    """

    success: bool
    plate_number: str
    plate_confidence: float
    vehicle_type: str  # "TRUCK" | "CAR" | "WAGON" | "UNKNOWN"
    vehicle_type_confidence: float
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_color: str | None = None
    error_message: str | None = None

    def to_legacy(self) -> PlateRecognitionResult:
        """Convert to legacy PlateRecognitionResult for backward compatibility."""
        return PlateRecognitionResult(
            plate_number=self.plate_number,
            confidence=self.plate_confidence,
            success=self.success,
            error_message=self.error_message,
        )


# Vehicle type mapping from PlateRecognizer API types to our internal types
VEHICLE_TYPE_MAP: dict[str, str] = {
    # Trucks and heavy vehicles -> TRUCK
    "Truck": "TRUCK",
    "Big Truck": "TRUCK",
    "Bus": "TRUCK",
    "Van": "TRUCK",
    "Trailer": "TRUCK",
    # Light vehicles -> CAR
    "Sedan": "CAR",
    "SUV": "CAR",
    "Pickup": "CAR",
    "Hatchback": "CAR",
    "Coupe": "CAR",
    "Convertible": "CAR",
    "Wagon": "CAR",  # Station wagon (not rail wagon)
    "Motorcycle": "CAR",  # Treat as light vehicle for gate purposes
    "Minivan": "CAR",
    # Unknown types
    "Unknown": "UNKNOWN",
}


def map_vehicle_type(api_type: str | None) -> str:
    """
    Map PlateRecognizer vehicle type to internal type.

    Args:
        api_type: Vehicle type string from PlateRecognizer API

    Returns:
        Internal vehicle type: "TRUCK", "CAR", "WAGON", or "UNKNOWN"
    """
    if not api_type:
        return "UNKNOWN"
    return VEHICLE_TYPE_MAP.get(api_type, "UNKNOWN")


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

    async def detect_vehicle(
        self, photo_bytes: bytes, region: str = "uz"
    ) -> VehicleDetectionResult:
        """
        Detect vehicle and recognize license plate from photo bytes.

        Enhanced version that extracts both plate number AND vehicle type/details.
        Use this method for gate camera integration where vehicle classification is needed.

        Args:
            photo_bytes: Image file bytes
            region: Region code for recognition (default: 'uz' for Uzbekistan)

        Returns:
            VehicleDetectionResult with plate number, vehicle type, and additional details
        """
        if not self.api_key:
            self.logger.error("API key not configured")
            return VehicleDetectionResult(
                success=False,
                plate_number="",
                plate_confidence=0.0,
                vehicle_type="UNKNOWN",
                vehicle_type_confidence=0.0,
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

                        error_msg = f"API error: {response.status}"
                        try:
                            error_json = json.loads(error_text)
                            if "detail" in error_json:
                                error_msg = f"API error: {error_json['detail']}"
                        except (json.JSONDecodeError, KeyError):
                            pass

                        return VehicleDetectionResult(
                            success=False,
                            plate_number="",
                            plate_confidence=0.0,
                            vehicle_type="UNKNOWN",
                            vehicle_type_confidence=0.0,
                            error_message=error_msg,
                        )

                    result = await response.json()
                    self.logger.info(f"PlateRecognizer raw response: {result}")

                    if result.get("results") and len(result["results"]) > 0:
                        best_result = result["results"][0]

                        # Extract plate data
                        plate = best_result.get("plate", "").strip().upper()
                        plate_confidence = best_result.get("score", 0.0)

                        # Extract vehicle data
                        vehicle_data = best_result.get("vehicle", {})
                        api_vehicle_type = vehicle_data.get("type")
                        vehicle_type = map_vehicle_type(api_vehicle_type)
                        vehicle_type_confidence = vehicle_data.get("score", 0.0)

                        # Extract additional vehicle details
                        make_data = vehicle_data.get("make", [])
                        model_data = vehicle_data.get("model", [])
                        color_data = vehicle_data.get("color", [])

                        vehicle_make = make_data[0].get("name") if make_data else None
                        vehicle_model = model_data[0].get("name") if model_data else None
                        vehicle_color = color_data[0].get("name") if color_data else None

                        if plate:
                            logger.info(
                                f"Detected plate: {plate} (confidence: {plate_confidence:.2%}), "
                                f"vehicle type: {vehicle_type} (API: {api_vehicle_type})"
                            )
                            return VehicleDetectionResult(
                                success=True,
                                plate_number=plate,
                                plate_confidence=plate_confidence,
                                vehicle_type=vehicle_type,
                                vehicle_type_confidence=vehicle_type_confidence,
                                vehicle_make=vehicle_make,
                                vehicle_model=vehicle_model,
                                vehicle_color=vehicle_color,
                            )
                        else:
                            logger.warning("API returned empty plate string")
                            return VehicleDetectionResult(
                                success=False,
                                plate_number="",
                                plate_confidence=0.0,
                                vehicle_type=vehicle_type,
                                vehicle_type_confidence=vehicle_type_confidence,
                                vehicle_make=vehicle_make,
                                vehicle_model=vehicle_model,
                                vehicle_color=vehicle_color,
                                error_message="Empty plate detected",
                            )
                    else:
                        logger.warning("No plates detected in image")
                        return VehicleDetectionResult(
                            success=False,
                            plate_number="",
                            plate_confidence=0.0,
                            vehicle_type="UNKNOWN",
                            vehicle_type_confidence=0.0,
                            error_message="No plates detected",
                        )

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP error during vehicle detection: {e!s}")
            return VehicleDetectionResult(
                success=False,
                plate_number="",
                plate_confidence=0.0,
                vehicle_type="UNKNOWN",
                vehicle_type_confidence=0.0,
                error_message="Network error",
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error during vehicle detection: {e!s}", exc_info=True
            )
            return VehicleDetectionResult(
                success=False,
                plate_number="",
                plate_confidence=0.0,
                vehicle_type="UNKNOWN",
                vehicle_type_confidence=0.0,
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
