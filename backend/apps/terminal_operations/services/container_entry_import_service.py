import io
from datetime import datetime
from typing import Any

import pandas as pd
from django.db import transaction
from django.utils import timezone

from apps.containers.models import Container
from apps.core.services import BaseService

from ..models import ContainerEntry, ContainerOwner


class ContainerEntryImportService(BaseService):
    """
    Service for importing container entries from Excel files.
    Handles parsing, validation, duplicate checking, and batch creation.
    """

    def __init__(self):
        super().__init__()
        self.batch_size = 100
        self.errors = []
        self.stats = {
            "total_rows": 0,
            "successful": 0,
            "skipped": 0,
            "failed": 0,
            "processing_time_seconds": 0,
        }

    def import_from_excel(self, file_input, user) -> dict[str, Any]:
        """
        Main import orchestrator - handles file reading and entry creation.

        Args:
            file_input: File object or bytes
            user: User making the import request

        Returns:
            Dict with success status, statistics, and any errors
        """
        start_time = timezone.now()
        self.errors = []
        self.stats = {
            "total_rows": 0,
            "successful": 0,
            "skipped": 0,
            "failed": 0,
            "processing_time_seconds": 0,
        }

        try:
            # Read Excel file
            df = self._read_excel_file(file_input)
            self.stats["total_rows"] = len(df)

            if len(df) == 0:
                return {
                    "success": False,
                    "message": "Excel file has no data rows",
                    "errors": ["File contains only headers or is empty"],
                }

            self.logger.info(f"Starting import of {len(df)} rows from Excel file")

            # Process rows in batches
            batch = []
            for idx, row in df.iterrows():
                row_num = idx + 2  # +2 because: 0-indexed + 1 header row

                try:
                    # Parse and validate row
                    parsed_row = self._parse_and_validate_row(row, row_num)
                    if parsed_row is None:
                        continue

                    # Check for existing entry with same container + entry_time
                    existing_entry = self._get_existing_entry(
                        parsed_row["container_number"], parsed_row["entry_time"]
                    )

                    if existing_entry:
                        # Update existing entry
                        self._update_entry(existing_entry, parsed_row)
                        self.stats["successful"] += 1
                        self.logger.debug(
                            f"Updated entry for {parsed_row['container_number']} on row {row_num}"
                        )
                        continue

                    # Add to batch for creating new entry
                    batch.append((parsed_row, user))

                    # Process batch when it reaches batch_size
                    if len(batch) >= self.batch_size:
                        self._process_batch(batch)
                        batch = []

                except Exception as e:
                    self.stats["failed"] += 1
                    error_msg = str(e)
                    container_num = row.get("Container number", "UNKNOWN")
                    self.errors.append(
                        {"row": row_num, "container": container_num, "error": error_msg}
                    )
                    self.logger.warning(f"Error processing row {row_num}: {error_msg}")

            # Process remaining batch
            if batch:
                self._process_batch(batch)

            # Calculate processing time
            elapsed = (timezone.now() - start_time).total_seconds()
            self.stats["processing_time_seconds"] = round(elapsed, 2)

            self.logger.info(
                f"Import completed: {self.stats['successful']} successful, "
                f"{self.stats['skipped']} skipped, {self.stats['failed']} failed"
            )

            return {
                "success": True,
                "message": "Import completed successfully",
                "statistics": self.stats,
                "errors": self.errors if self.errors else None,
            }

        except Exception as e:
            self.logger.error(f"Fatal error during import: {e!s}", exc_info=True)
            return {
                "success": False,
                "message": f"Import failed: {e!s}",
                "statistics": self.stats,
                "errors": self.errors,
            }

    @transaction.atomic
    def _process_batch(self, batch: list[tuple[dict, Any]]):
        """
        Process a batch of parsed rows atomically.

        Args:
            batch: List of (parsed_row_dict, user) tuples
        """
        for parsed_row, user in batch:
            try:
                # Get or create container
                container = self._get_or_create_container(
                    parsed_row["container_number"], parsed_row["container_iso_type"]
                )

                # Create container entry
                ContainerEntry.objects.create(
                    container=container,
                    status=parsed_row["status"],
                    transport_type=parsed_row["transport_type"],
                    transport_number=parsed_row.get("transport_number", ""),
                    entry_train_number=parsed_row.get("entry_train_number", ""),
                    entry_time=parsed_row["entry_time"],
                    recorded_by=user,
                    # Stage 2 fields
                    client_name=parsed_row.get("client_name", ""),
                    container_owner=parsed_row.get("container_owner", ""),
                    cargo_name=parsed_row.get("cargo_name", ""),
                    cargo_weight=parsed_row.get("cargo_weight"),
                    location=parsed_row.get("location", ""),
                    additional_crane_operation_date=parsed_row.get(
                        "additional_crane_operation_date"
                    ),
                    note=parsed_row.get("note", ""),
                    # Stage 3 fields
                    exit_date=parsed_row.get("exit_date"),
                    exit_transport_type=parsed_row.get("exit_transport_type"),
                    exit_train_number=parsed_row.get("exit_train_number", ""),
                    exit_transport_number=parsed_row.get("exit_transport_number", ""),
                    destination_station=parsed_row.get("destination_station", ""),
                    # Note: dwell_time_days is a computed property, not stored
                )

                self.stats["successful"] += 1

            except Exception as e:
                self.stats["failed"] += 1
                self.logger.error(f"Error creating entry: {e!s}", exc_info=True)
                raise

    def _read_excel_file(self, file_input) -> pd.DataFrame:
        """
        Read Excel file using pandas.
        Handles both English headers (with Russian translation row) and direct Russian headers.

        Args:
            file_input: File object or bytes

        Returns:
            DataFrame with data rows only (uses Russian column names)
        """
        if isinstance(file_input, bytes):
            file_input = io.BytesIO(file_input)

        # Read Excel file with English headers (first row)
        df = pd.read_excel(file_input)

        # Check if first data row contains Russian translations (indicating English headers)
        if len(df) > 0:
            first_row = df.iloc[0]
            # If first row has text values in first columns, it's likely the Russian translation row
            if all(
                isinstance(v, str) and len(str(v)) > 0 for v in first_row.values[:5]
            ):
                # Use first row values as Russian column names
                df.columns = first_row.values
                # Skip the translation row (first data row)
                df = df.iloc[1:].reset_index(drop=True)

        # Remove completely empty rows
        df = df.dropna(how="all")

        # Replace NaN/None with empty strings
        df = df.fillna("").infer_objects(copy=False)

        return df.reset_index(drop=True)

    def _parse_and_validate_row(
        self, row: pd.Series, row_num: int
    ) -> dict[str, Any] | None:
        """
        Parse and validate a single Excel row (with Russian column names).
        Returns None if row should be skipped (e.g., empty/invalid).

        Args:
            row: Pandas Series representing a row
            row_num: Row number (for error reporting)

        Returns:
            Dict with parsed data or None if invalid
        """
        # Get container number (required) - Russian column name
        container_number = str(row.get("Номер контейнера", "")).strip()
        if not container_number or container_number.upper() == "NAN":
            raise ValueError("Missing or invalid container number")

        # Get ISO type (required) - Russian column name
        iso_type = str(row.get("Тип", "")).strip().upper()
        if not iso_type or iso_type == "NAN":
            raise ValueError("Missing or invalid container type")

        # Validate ISO type exists in model
        valid_types = [choice[0] for choice in Container.ISO_TYPE_CHOICES]
        if iso_type not in valid_types:
            raise ValueError(
                f"Invalid ISO type '{iso_type}'. Valid types: {', '.join(valid_types[:5])}..."
            )

        # Parse entry date (required) - Russian column name
        entry_date_str = row.get("Дата разгрузки на терминале", "")
        entry_date = self._parse_datetime(entry_date_str)
        if not entry_date:
            raise ValueError(f"Invalid or missing entry date: {entry_date_str}")

        # Map transport type - Russian column name with newline
        transport_type_raw = str(row.get("транспорт\nпри ЗАВОЗЕ", "")).strip().lower()
        transport_type = self._map_transport_type(transport_type_raw)
        if not transport_type:
            raise ValueError(f"Invalid transport type: {transport_type_raw}")

        # Parse optional exit date - Russian column name
        exit_date_str = row.get("Дата вывоза конт-ра с МТТ", "")
        exit_date = self._parse_datetime(exit_date_str) if exit_date_str else None

        # Map exit transport type - Russian column name with newline
        exit_transport_type_raw = row.get("Транспорт\nпри ВЫВОЗЕ", "")
        exit_transport_type = None
        if (
            exit_transport_type_raw
            and str(exit_transport_type_raw).strip().lower() != "nan"
        ):
            exit_transport_type = self._map_transport_type(
                str(exit_transport_type_raw).strip().lower()
            )

        # Parse other optional fields - Russian column names
        dwell_time_str = str(row.get("Количество дней на хранение", "")).strip()
        dwell_time_days = None
        if dwell_time_str and dwell_time_str != "nan":
            try:
                dwell_time_days = int(float(dwell_time_str))
            except (ValueError, TypeError):
                pass

        weight_str = str(row.get("Тоннаж", "")).strip()
        cargo_weight = None
        if weight_str and weight_str != "nan":
            try:
                cargo_weight = float(weight_str)
            except (ValueError, TypeError):
                pass

        additional_crane_date_str = row.get("дата дополнительной крановой операции", "")
        additional_crane_operation_date = None
        if (
            additional_crane_date_str
            and str(additional_crane_date_str).strip().lower() != "nan"
        ):
            additional_crane_operation_date = self._parse_datetime(
                str(additional_crane_date_str)
            )

        # Build parsed row dict
        return {
            "container_number": container_number.upper(),
            "container_iso_type": iso_type,
            "status": "EMPTY",  # All records in this file are empty
            "transport_type": transport_type,
            "transport_number": self._clean_value(
                row.get("номер машины/ вагона \nпри ЗАВОЗЕ", "")
            ),
            "entry_train_number": self._clean_value(
                row.get("Номер Поезда\nпри ЗАВОЗЕ", "")
            ),
            "entry_time": entry_date,
            "client_name": self._clean_value(row.get("Клиент", "")),
            "container_owner": self._get_or_create_container_owner(
                self._clean_value(row.get("Собственник контейнера", ""))
            ),
            "cargo_name": self._clean_value(row.get("Наименование ГРУЗА", "")),
            "cargo_weight": cargo_weight,
            "location": self._clean_value(row.get("Местоположение", "")),
            "additional_crane_operation_date": additional_crane_operation_date,
            "note": self._clean_value(row.get("Примечание", "")),
            "exit_date": exit_date,
            "exit_transport_type": exit_transport_type,
            "exit_train_number": self._clean_value(
                row.get("Номер Поезда\nпри ВЫВОЗЕ", "")
            ),
            "exit_transport_number": self._clean_value(
                row.get("номер машины/ вагона \nпри ВЫВОЗЕ", "")
            ),
            "destination_station": self._clean_value(row.get("Станция назначения", "")),
            "dwell_time_days": dwell_time_days,
        }

    def _get_existing_entry(
        self, container_number: str, entry_time: datetime
    ) -> ContainerEntry | None:
        """
        Check if an entry exists for the same container and entry_time.
        This is used to determine if we should update an existing entry
        or create a new one during import.

        Args:
            container_number: Container number to check
            entry_time: Entry time to check

        Returns:
            Existing ContainerEntry if found, None otherwise
        """
        try:
            # Check for exact match on container_number and entry_time (ignoring seconds/microseconds)
            return ContainerEntry.objects.filter(
                container__container_number=container_number.upper(),
                entry_time__date=entry_time.date(),
                entry_time__hour=entry_time.hour,
                entry_time__minute=entry_time.minute,
            ).first()
        except Exception as e:
            self.logger.error(f"Error checking for existing entry: {e}")
            return None

    @transaction.atomic
    def _update_entry(self, entry: ContainerEntry, parsed_row: dict[str, Any]):
        """
        Update an existing container entry with new data from the import.

        Args:
            entry: Existing ContainerEntry instance to update
            parsed_row: Parsed row data from Excel
        """
        # Update basic fields
        entry.status = parsed_row.get("status", entry.status)
        entry.transport_type = parsed_row.get("transport_type", entry.transport_type)
        entry.transport_number = parsed_row.get(
            "transport_number", entry.transport_number
        )
        entry.entry_train_number = parsed_row.get(
            "entry_train_number", entry.entry_train_number
        )

        # Update business info fields
        entry.client_name = parsed_row.get("client_name", entry.client_name)
        entry.container_owner = parsed_row.get("container_owner", entry.container_owner)
        entry.cargo_name = parsed_row.get("cargo_name", entry.cargo_name)
        entry.cargo_weight = parsed_row.get("cargo_weight", entry.cargo_weight)
        entry.location = parsed_row.get("location", entry.location)
        entry.additional_crane_operation_date = parsed_row.get(
            "additional_crane_operation_date", entry.additional_crane_operation_date
        )
        entry.note = parsed_row.get("note", entry.note)

        # Update exit information fields
        entry.exit_date = parsed_row.get("exit_date", entry.exit_date)
        entry.exit_transport_type = parsed_row.get(
            "exit_transport_type", entry.exit_transport_type
        )
        entry.exit_train_number = parsed_row.get(
            "exit_train_number", entry.exit_train_number
        )
        entry.exit_transport_number = parsed_row.get(
            "exit_transport_number", entry.exit_transport_number
        )
        entry.destination_station = parsed_row.get(
            "destination_station", entry.destination_station
        )
        # Note: dwell_time_days is a computed property, not stored

        # Save the updated entry
        entry.save()
        self.logger.info(
            f"Updated entry {entry.id} for container {entry.container.container_number}"
        )

    def _should_skip_duplicate(
        self, container_number: str, entry_date: datetime
    ) -> bool:
        """
        Smart duplicate check:
        - Skip if entry exists for same date AND has NOT exited (exit_date is NULL)
        - Allow if entry exists for same date but HAS exited (container can return)

        Args:
            container_number: Container number to check
            entry_date: Entry date to check

        Returns:
            True if should skip, False if should create new entry
        """
        entry_date_only = entry_date.date()

        # Check if entry exists for same date
        existing_entry = ContainerEntry.objects.filter(
            container__container_number=container_number.upper(),
            entry_time__date=entry_date_only,
        ).first()

        if not existing_entry:
            return False  # No existing entry, create new one

        # Entry exists - check if it has exited
        if existing_entry.exit_date is None:
            # Container is still on terminal - skip duplicate
            return True

        # Container has exited - allow new entry
        return False

    def _clean_value(self, value) -> str:
        """
        Clean a value: convert to string, strip whitespace, remove 'nan' strings.

        Args:
            value: Value to clean (can be any type)

        Returns:
            Empty string if value is None/empty/nan, otherwise cleaned string
        """
        if value is None or value == "":
            return ""

        str_value = str(value).strip()

        # Check for pandas NaT or NaN strings
        if str_value.lower() in ["nan", "nat", "<nat>", "none"]:
            return ""

        return str_value

    def _map_transport_type(self, value: str) -> str | None:
        """
        Map transport type values from Excel to model values.

        Args:
            value: Raw value from Excel (lowercase)

        Returns:
            Mapped value ('TRUCK' or 'WAGON') or None if invalid
        """
        if not value:
            return None

        value_lower = str(value).strip().lower()

        # Map variations
        if value_lower == "truck":
            return "TRUCK"
        elif value_lower == "wagon":
            return "WAGON"
        elif value_lower == "train":
            return "TRAIN"

        return None

    def _parse_datetime(self, value: str | float | datetime) -> datetime | None:
        """
        Parse datetime value from Excel with timezone awareness.

        Args:
            value: Value to parse (string, float, or datetime)

        Returns:
            Timezone-aware datetime or None if invalid
        """
        if value is None or str(value).strip() == "" or str(value).lower() == "nan":
            return None

        try:
            # If already a datetime, ensure timezone aware
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    return timezone.make_aware(value, timezone.get_current_timezone())
                return value

            # Try parsing as string
            if isinstance(value, str):
                # Try common date formats
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                    try:
                        parsed = datetime.strptime(value.strip(), fmt)
                        return timezone.make_aware(
                            parsed, timezone.get_current_timezone()
                        )
                    except ValueError:
                        continue

            # Try pandas Timestamp conversion
            ts = pd.Timestamp(value)
            dt = ts.to_pydatetime()
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt

        except (ValueError, TypeError, pd.errors.ParserError):
            self.logger.warning(f"Could not parse datetime: {value}")
            return None

    def _get_or_create_container(
        self, container_number: str, iso_type: str
    ) -> Container:
        """
        Get or create a Container instance.

        Args:
            container_number: Container number (4 letters + 7 digits)
            iso_type: ISO type code

        Returns:
            Container instance
        """
        container, created = Container.objects.get_or_create(
            container_number=container_number.upper(),
            defaults={"iso_type": iso_type.upper()},
        )

        # Update ISO type if different
        if not created and container.iso_type != iso_type.upper():
            container.iso_type = iso_type.upper()
            container.save(update_fields=["iso_type"])

        return container

    def _get_or_create_container_owner(self, owner_name: str) -> ContainerOwner | None:
        """
        Get or create a ContainerOwner instance by name.
        Handles slug collision by searching case-insensitively first.

        Args:
            owner_name: Owner name from Excel

        Returns:
            ContainerOwner instance or None if name is empty
        """
        if not owner_name or owner_name.strip() == "":
            return None

        owner_name = owner_name.strip()

        # First, try to find existing owner by name (case-insensitive)
        existing_owner = ContainerOwner.objects.filter(name__iexact=owner_name).first()
        if existing_owner:
            return existing_owner

        # Create new owner - let the save() method handle slug generation
        try:
            owner = ContainerOwner.objects.create(name=owner_name)
            self.logger.info(f"Created new ContainerOwner: {owner_name}")
            return owner
        except Exception as e:
            # If slug collision occurs despite name check, log warning and retry with exact name match
            self.logger.warning(f"Error creating ContainerOwner '{owner_name}': {e}")
            # Return existing owner with same name if it exists
            return ContainerOwner.objects.filter(name__iexact=owner_name).first()
