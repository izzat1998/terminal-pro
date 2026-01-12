from django.db import transaction

from apps.core.services import BaseService

from .preorder_service import PreOrderService


class GateMatchingService(BaseService):
    """
    Service for matching pre-orders at the gate when security scans plates.
    Acts as an integration layer between PreOrderService and entry creation.
    """

    def __init__(self):
        super().__init__()
        self.preorder_service = PreOrderService()

    def check_preorder_match(self, plate_number):
        """
        Check if there's a pending pre-order for this plate.
        Called when security scans a plate at the gate.

        Args:
            plate_number: Scanned plate number

        Returns:
            dict with:
                - matched: bool
                - preorder: PreOrder instance or None
                - prefill_data: dict with fields to pre-fill in entry form
        """
        preorder = self.preorder_service.match_by_plate(plate_number)

        if not preorder:
            return {"matched": False, "preorder": None, "prefill_data": {}}

        # Build prefill data for ContainerEntry form
        prefill_data = {
            "transport_number": preorder.plate_number,
            "transport_type": "TRUCK",  # Pre-orders are always trucks
            "operation_hint": preorder.operation_type,  # LOAD = likely EMPTY, UNLOAD = likely LADEN
            "customer_name": preorder.customer.full_name if preorder.customer else "",
            "customer_phone": preorder.customer.phone_number
            if preorder.customer
            else "",
        }

        # Suggest container status based on operation type
        # LOAD = customer bringing empty container for loading = status EMPTY
        # UNLOAD = customer bringing full container for unloading = status LADEN
        if preorder.operation_type == "LOAD":
            prefill_data["suggested_status"] = "EMPTY"
        else:
            prefill_data["suggested_status"] = "LADEN"

        # Include truck photo reference if available
        if preorder.truck_photo:
            prefill_data["truck_photo_id"] = preorder.truck_photo.id
            prefill_data["truck_photo_url"] = (
                preorder.truck_photo.file.url if preorder.truck_photo.file else None
            )

        self.logger.info(
            f"Pre-order match found: #{preorder.id} for plate {plate_number} "
            f"(customer: {prefill_data['customer_name']})"
        )

        return {"matched": True, "preorder": preorder, "prefill_data": prefill_data}

    @transaction.atomic
    def complete_match(self, preorder_id, entry):
        """
        Complete the match by linking pre-order to created entry.
        Called after security creates the ContainerEntry.

        Args:
            preorder_id: PreOrder ID
            entry: ContainerEntry instance that was created

        Returns:
            Updated PreOrder instance
        """
        from ..models import PreOrder

        try:
            preorder = PreOrder.objects.get(id=preorder_id)
        except PreOrder.DoesNotExist:
            self.logger.warning(f"Pre-order #{preorder_id} not found for completion")
            return None

        return self.preorder_service.complete_order(preorder, entry)

    def get_matching_summary(self, plate_number):
        """
        Get a human-readable summary of pre-order match.
        Useful for displaying to security at the gate.

        Args:
            plate_number: Scanned plate number

        Returns:
            Dict with summary info or None if no match
        """
        result = self.check_preorder_match(plate_number)

        if not result["matched"]:
            return None

        preorder = result["preorder"]
        operation_text = (
            "Погрузка" if preorder.operation_type == "LOAD" else "Разгрузка"
        )

        return {
            "preorder_id": preorder.id,
            "plate_number": preorder.plate_number,
            "operation_type": preorder.operation_type,
            "operation_text": operation_text,
            "customer_name": preorder.customer.full_name
            if preorder.customer
            else "Неизвестно",
            "customer_phone": preorder.customer.phone_number
            if preorder.customer
            else "",
            "created_at": preorder.created_at,
            "suggested_status": result["prefill_data"].get("suggested_status", ""),
            "has_photo": preorder.truck_photo is not None,
            "notes": preorder.notes,
        }
