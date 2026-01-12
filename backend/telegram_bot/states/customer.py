from aiogram.fsm.state import State, StatesGroup


class CustomerPreOrderForm(StatesGroup):
    """FSM states for customer pre-order creation (multi-plate flow)"""

    plate_numbers = State()  # Enter multiple plate numbers (one per line)
    operation_type = State()  # Select LOAD/UNLOAD for current plate
    confirmation = State()  # Show summary and confirm all


class CustomerOrderManagement(StatesGroup):
    """FSM states for viewing/cancelling orders"""

    viewing_orders = State()  # Viewing order list
    cancel_confirmation = State()  # Confirming cancellation


class CustomerContainerCabinet(StatesGroup):
    """FSM states for browsing company containers"""

    viewing_list = State()  # Paginated container list
    searching = State()  # Search by container number
    viewing_details = State()  # Container detail card
