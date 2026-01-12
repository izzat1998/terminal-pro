from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService

from ..models import PreOrder


class PreOrderService(BaseService):
    """
    Business logic for customer pre-orders.
    Handles pre-order creation, cancellation, and plate matching.
    """

    def _normalize_plate(self, plate_number):
        """
        Normalize plate number for consistent matching.
        Removes spaces, dashes, converts to uppercase.

        Args:
            plate_number: Raw plate number string

        Returns:
            Normalized plate number
        """
        if not plate_number:
            return ""
        return plate_number.upper().replace(" ", "").replace("-", "").replace(".", "")

    @transaction.atomic
    def create_preorder(
        self, customer, plate_number, operation_type, truck_photo=None, notes="", batch_id=None
    ):
        """
        Create new pre-order for customer.

        Args:
            customer: CustomUser instance (customer)
            plate_number: Vehicle plate number
            operation_type: LOAD or UNLOAD
            truck_photo: File instance (optional)
            notes: Optional notes
            batch_id: UUID for grouping orders created together (optional)

        Returns:
            PreOrder instance

        Raises:
            BusinessLogicError: If validation fails
        """
        # Validate operation type
        valid_operations = ["LOAD", "UNLOAD"]
        if operation_type not in valid_operations:
            raise BusinessLogicError(
                message=f"Неверный тип операции. Допустимые: {valid_operations}",
                error_code="INVALID_OPERATION_TYPE",
                details={"operation_type": operation_type},
            )

        # Validate plate number
        if not plate_number or len(plate_number.strip()) < 3:
            raise BusinessLogicError(
                message="Номер автомобиля должен содержать минимум 3 символа",
                error_code="INVALID_PLATE_NUMBER",
                details={"plate_number": plate_number},
            )

        # Normalize plate number
        normalized_plate = self._normalize_plate(plate_number)

        # Create pre-order
        preorder = PreOrder.objects.create(
            customer=customer,
            plate_number=normalized_plate,
            operation_type=operation_type,
            truck_photo=truck_photo,
            notes=notes,
            status="PENDING",
            batch_id=batch_id,
        )

        self.logger.info(
            f"Created pre-order #{preorder.id} for customer {customer.first_name}: "
            f"{normalized_plate} ({operation_type})"
            f"{f' [batch: {batch_id}]' if batch_id else ''}"
        )

        return preorder

    def get_customer_orders(self, customer, status=None, limit=None):
        """
        Get all pre-orders for a customer, optionally filtered by status.

        Args:
            customer: CustomUser instance
            status: Optional status filter (PENDING, MATCHED, COMPLETED, CANCELLED)
            limit: Optional limit on number of results

        Returns:
            QuerySet of PreOrder instances
        """
        queryset = PreOrder.objects.filter(customer=customer)

        if status:
            queryset = queryset.filter(status=status)

        queryset = queryset.select_related("truck_photo", "matched_entry").order_by(
            "-created_at"
        )

        if limit:
            queryset = queryset[:limit]

        return queryset

    def get_pending_orders(self, customer):
        """
        Get pending orders for customer.

        Args:
            customer: CustomUser instance

        Returns:
            QuerySet of pending PreOrder instances
        """
        return self.get_customer_orders(customer, status="PENDING")

    def get_order_by_id(self, order_id, customer=None):
        """
        Get pre-order by ID, optionally validating customer ownership.

        Args:
            order_id: PreOrder ID
            customer: Optional CustomUser instance for ownership validation

        Returns:
            PreOrder instance

        Raises:
            BusinessLogicError: If order not found or not owned by customer
        """
        try:
            queryset = PreOrder.objects.select_related(
                "customer", "truck_photo", "matched_entry"
            )
            if customer:
                queryset = queryset.filter(customer=customer)
            return queryset.get(id=order_id)
        except PreOrder.DoesNotExist:
            raise BusinessLogicError(
                message="Заявка не найдена",
                error_code="ORDER_NOT_FOUND",
                details={"order_id": order_id},
            )

    @transaction.atomic
    def cancel_order(self, order_id, customer):
        """
        Cancel a pending pre-order.

        Args:
            order_id: PreOrder ID
            customer: CustomUser instance (for ownership validation)

        Returns:
            Cancelled PreOrder instance

        Raises:
            BusinessLogicError: If order not found, not owned, or not pending
        """
        preorder = self.get_order_by_id(order_id, customer)

        if preorder.status != "PENDING":
            raise BusinessLogicError(
                message="Можно отменить только активные заявки",
                error_code="ORDER_NOT_PENDING",
                details={"order_id": order_id, "current_status": preorder.status},
            )

        preorder.status = "CANCELLED"
        preorder.cancelled_at = timezone.now()
        preorder.save()

        self.logger.info(
            f"Cancelled pre-order #{preorder.id} ({preorder.plate_number}) "
            f"by customer {customer.first_name}"
        )

        return preorder

    def match_by_plate(self, plate_number):
        """
        Find pending pre-order by plate number for gate matching.

        Args:
            plate_number: Vehicle plate scanned at gate

        Returns:
            PreOrder instance or None
        """
        normalized_plate = self._normalize_plate(plate_number)

        if not normalized_plate:
            return None

        # Find first pending pre-order with matching plate
        return (
            PreOrder.objects.filter(plate_number=normalized_plate, status="PENDING")
            .select_related("customer", "truck_photo")
            .first()
        )

    @transaction.atomic
    def mark_matched(self, preorder, entry=None):
        """
        Mark pre-order as matched when vehicle arrives.

        Args:
            preorder: PreOrder instance
            entry: Optional ContainerEntry that was created

        Returns:
            Updated PreOrder instance
        """
        preorder.status = "MATCHED"
        preorder.matched_at = timezone.now()

        if entry:
            preorder.matched_entry = entry
            preorder.status = "COMPLETED"

        preorder.save()

        self.logger.info(
            f"Matched pre-order #{preorder.id} ({preorder.plate_number}) "
            f"{'with entry' if entry else 'at gate'}"
        )

        return preorder

    @transaction.atomic
    def complete_order(self, preorder, entry):
        """
        Complete pre-order by linking it to a created container entry.

        Args:
            preorder: PreOrder instance
            entry: ContainerEntry instance

        Returns:
            Updated PreOrder instance
        """
        preorder.matched_entry = entry
        preorder.status = "COMPLETED"
        if not preorder.matched_at:
            preorder.matched_at = timezone.now()
        preorder.save()

        self.logger.info(f"Completed pre-order #{preorder.id} -> entry #{entry.id}")

        return preorder

    def get_pending_orders_count(self, customer):
        """
        Get count of pending orders for customer.

        Args:
            customer: CustomUser instance

        Returns:
            Integer count
        """
        return PreOrder.objects.filter(customer=customer, status="PENDING").count()

    def get_all_pending_orders(self, limit=100):
        """
        Get all pending pre-orders (for admin view).

        Args:
            limit: Maximum number of results

        Returns:
            QuerySet of PreOrder instances
        """
        return (
            PreOrder.objects.filter(status="PENDING")
            .select_related("customer", "truck_photo")
            .order_by("-created_at")[:limit]
        )

    def get_orders_stats(self):
        """
        Get pre-order statistics (for admin dashboard).

        Returns:
            Dict with statistics
        """
        stats = PreOrder.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="PENDING")),
            matched=Count("id", filter=Q(status="MATCHED")),
            completed=Count("id", filter=Q(status="COMPLETED")),
            cancelled=Count("id", filter=Q(status="CANCELLED")),
        )

        return stats
