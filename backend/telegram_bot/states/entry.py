from aiogram.fsm.state import State, StatesGroup


class LanguageSelection(StatesGroup):
    """FSM state for language selection"""

    choosing = State()


class PhoneVerification(StatesGroup):
    """FSM states for phone verification and manager access"""

    waiting_for_phone = State()


class EntryForm(StatesGroup):
    """FSM states for container entry creation"""

    container_number = State()
    container_iso_type = State()
    container_owner = State()
    status = State()
    transport_type = State()
    transport_plate_photo = (
        State()
    )  # NEW: Photo recognition for truck plates (only TRUCK type)
    transport_number = State()
    photos = State()
    confirmation = State()


class ExitForm(StatesGroup):
    """FSM states for container exit registration"""

    container_number = State()
    exit_date = State()
    exit_transport_type = State()
    exit_transport_number = State()
    exit_train_number = State()
    destination_station = State()
    crane_operations = State()
    photos = State()
    confirmation = State()


class CraneOperationForm(StatesGroup):
    """FSM states for adding crane operations to containers on terminal"""

    container_number = State()
    adding_operations = State()
