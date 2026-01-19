"""
Data migration to convert existing WorkOrder statuses to simplified workflow.

Conversion rules:
- VERIFIED, COMPLETED → COMPLETED
- FAILED → COMPLETED (no failure status in new workflow)
- PENDING, ASSIGNED, ACCEPTED, IN_PROGRESS → PENDING
"""

from django.db import migrations


def convert_statuses_forward(apps, schema_editor):
    """Convert old statuses to new simplified statuses."""
    WorkOrder = apps.get_model("terminal_operations", "WorkOrder")

    # VERIFIED, COMPLETED, FAILED → COMPLETED
    completed_statuses = ["VERIFIED", "COMPLETED", "FAILED"]
    WorkOrder.objects.filter(status__in=completed_statuses).update(status="COMPLETED")

    # PENDING, ASSIGNED, ACCEPTED, IN_PROGRESS → PENDING
    pending_statuses = ["PENDING", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"]
    WorkOrder.objects.filter(status__in=pending_statuses).update(status="PENDING")


def convert_statuses_backward(apps, schema_editor):
    """
    Reverse migration - convert back to old statuses.
    Note: This is a lossy operation since we can't know the original status.
    COMPLETED → VERIFIED, PENDING → PENDING
    """
    WorkOrder = apps.get_model("terminal_operations", "WorkOrder")

    # COMPLETED → VERIFIED (best guess for completed work orders)
    WorkOrder.objects.filter(status="COMPLETED").update(status="VERIFIED")

    # PENDING stays PENDING


class Migration(migrations.Migration):

    dependencies = [
        ("terminal_operations", "0021_simplify_workorder_status"),
    ]

    operations = [
        migrations.RunPython(convert_statuses_forward, convert_statuses_backward),
    ]
