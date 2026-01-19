"""
Verify integrity and realism of generated MTT presentation data.

This verification script checks:
1. Foreign key chains (all relationships valid)
2. Timestamp sequences (logical chronological order)
3. Business rules (row segregation, stacking, etc.)
4. Distribution validation (70/30 ratios maintained)
5. Occupancy grid consistency
6. Complete audit trails
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone

from apps.terminal_operations.models import (
    ContainerEntry,
    ContainerPosition,
    PreOrder,
    WorkOrder,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Verify integrity and realism of generated presentation data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed validation information",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to fix issues (use with caution)",
        )

    def handle(self, *args, **options):
        self.verbosity = 2 if options["verbose"] else 1
        self.fix_mode = options["fix"]

        if self.fix_mode:
            self.stdout.write(self.style.WARNING("\n⚠️  FIX MODE ENABLED - Will attempt to fix issues\n"))

        self.stdout.write(self.style.NOTICE("🔍 Starting data integrity verification...\n"))

        # Track issues
        self.issues = []
        self.warnings = []

        # Run all validation checks
        self._check_foreign_keys()
        self._check_timestamp_sequences()
        self._check_business_rules()
        self._check_distributions()
        self._check_occupancy_consistency()
        self._check_audit_trails()

        # Print summary
        self._print_summary()

    def _check_foreign_keys(self):
        """Validate all foreign key relationships"""
        self._log_section("1. Foreign Key Validation")

        checks = [
            ("ContainerEntry.container", ContainerEntry.objects.filter(container__isnull=True)),
            ("ContainerEntry.recorded_by", ContainerEntry.objects.filter(recorded_by__isnull=True)),
            ("ContainerEntry.company", ContainerEntry.objects.filter(company__isnull=True)),
            ("WorkOrder.container_entry", WorkOrder.objects.filter(container_entry__isnull=True)),
            ("WorkOrder.created_by", WorkOrder.objects.filter(created_by__isnull=True)),
            ("WorkOrder.assigned_to_vehicle", WorkOrder.objects.filter(assigned_to_vehicle__isnull=True)),
            ("ContainerPosition.container_entry", ContainerPosition.objects.filter(container_entry__isnull=True)),
            ("PreOrder.customer", PreOrder.objects.filter(customer__isnull=True)),
        ]

        all_valid = True
        for name, queryset in checks:
            count = queryset.count()
            if count > 0:
                self._add_issue(f"Found {count} records with NULL {name}")
                all_valid = False
            else:
                self._log_pass(f"{name}: OK")

        if all_valid:
            self._log_pass("All foreign keys valid")

    def _check_timestamp_sequences(self):
        """Validate chronological order of timestamps"""
        self._log_section("2. Timestamp Sequence Validation")

        issues_found = 0

        # Check: entry_time < work_order.created_at
        entries_with_wo = ContainerEntry.objects.filter(
            work_orders__isnull=False
        ).distinct()

        for entry in entries_with_wo:
            for wo in entry.work_orders.all():
                if wo.created_at and wo.created_at < entry.entry_time:
                    self._add_issue(
                        f"Entry {entry.id}: work_order.created_at ({wo.created_at}) "
                        f"before entry_time ({entry.entry_time})"
                    )
                    issues_found += 1

                # Check work order internal sequence
                if wo.assigned_at and wo.created_at and wo.assigned_at < wo.created_at:
                    self._add_issue(f"WorkOrder {wo.id}: assigned_at before created_at")
                    issues_found += 1

                if wo.accepted_at and wo.assigned_at and wo.accepted_at < wo.assigned_at:
                    self._add_issue(f"WorkOrder {wo.id}: accepted_at before assigned_at")
                    issues_found += 1

                if wo.started_at and wo.accepted_at and wo.started_at < wo.accepted_at:
                    self._add_issue(f"WorkOrder {wo.id}: started_at before accepted_at")
                    issues_found += 1

                if wo.completed_at and wo.started_at and wo.completed_at < wo.started_at:
                    self._add_issue(f"WorkOrder {wo.id}: completed_at before started_at")
                    issues_found += 1

                if wo.verified_at and wo.completed_at and wo.verified_at < wo.completed_at:
                    self._add_issue(f"WorkOrder {wo.id}: verified_at before completed_at")
                    issues_found += 1

        # Check: exit_date > entry_time
        invalid_exits = ContainerEntry.objects.filter(
            exit_date__isnull=False
        ).filter(
            exit_date__lt=F("entry_time")
        ).count()

        if invalid_exits > 0:
            self._add_issue(f"Found {invalid_exits} entries with exit_date before entry_time")
            issues_found += invalid_exits

        # Check: PreOrder.created_at < matched_at
        invalid_preorders = PreOrder.objects.filter(
            matched_at__isnull=False
        ).filter(
            matched_at__lt=F("created_at")
        ).count()

        if invalid_preorders > 0:
            self._add_issue(f"Found {invalid_preorders} pre-orders with matched_at before created_at")
            issues_found += invalid_preorders

        if issues_found == 0:
            self._log_pass("All timestamp sequences valid")
        else:
            self._log_fail(f"Found {issues_found} timestamp sequence issues")

    def _check_business_rules(self):
        """Validate business rules compliance"""
        self._log_section("3. Business Rules Validation")

        issues_found = 0

        # Rule 1: Row segregation (40ft in rows 1-5, 20ft in rows 6-10)
        positions = ContainerPosition.objects.select_related("container_entry__container").all()

        for position in positions:
            iso_type = position.container_entry.container.iso_type
            size_code = iso_type[0] if iso_type else "2"
            is_40ft = size_code in ["4", "L"]

            if is_40ft and position.row not in range(1, 6):
                self._add_issue(
                    f"Position {position.id}: 40ft container in row {position.row} "
                    f"(should be 1-5)"
                )
                issues_found += 1

            if not is_40ft and position.row not in range(6, 11):
                self._add_issue(
                    f"Position {position.id}: 20ft container in row {position.row} "
                    f"(should be 6-10)"
                )
                issues_found += 1

        # Rule 2: Stacking validation
        position_dict = {}
        for position in positions:
            key = (position.zone, position.row, position.bay, position.tier, position.sub_slot)
            position_dict[key] = position

        for (zone, row, bay, tier, slot), position in position_dict.items():
            if tier > 1:
                # Check support below
                below_key = (zone, row, bay, tier - 1, slot)
                if below_key not in position_dict:
                    self._add_warning(
                        f"Position {position.id}: Tier {tier} without support at tier {tier - 1}"
                    )
                    issues_found += 1
                else:
                    # Check size compatibility
                    pos_below = position_dict[below_key]
                    iso_top = position.container_entry.container.iso_type
                    iso_below = pos_below.container_entry.container.iso_type

                    size_top = iso_top[0] if iso_top else "2"
                    size_below = iso_below[0] if iso_below else "2"

                    is_40ft_top = size_top in ["4", "L"]
                    is_40ft_below = size_below in ["4", "L"]

                    if is_40ft_top and not is_40ft_below:
                        self._add_issue(
                            f"Position {position.id}: 40ft container on 20ft container"
                        )
                        issues_found += 1

                    # Check weight distribution
                    if position.container_entry.status == "LADEN" and pos_below.container_entry.status == "EMPTY":
                        self._add_issue(
                            f"Position {position.id}: LADEN container on EMPTY container"
                        )
                        issues_found += 1

        # Rule 3: ISO type matches container size
        entries = ContainerEntry.objects.select_related("container").all()
        for entry in entries:
            iso_type = entry.container.iso_type
            if iso_type:
                size_code = iso_type[0]
                if size_code not in ["2", "4", "L"]:
                    self._add_issue(
                        f"Entry {entry.id}: Invalid ISO type size code '{size_code}'"
                    )
                    issues_found += 1

        # Rule 4: LADEN containers have cargo details
        laden_without_cargo = ContainerEntry.objects.filter(
            status="LADEN"
        ).filter(
            Q(cargo_name__isnull=True) | Q(cargo_name="")
        ).count()

        if laden_without_cargo > 0:
            self._add_warning(f"Found {laden_without_cargo} LADEN containers without cargo_name")

        if issues_found == 0:
            self._log_pass("All business rules compliant")
        else:
            self._log_fail(f"Found {issues_found} business rule violations")

    def _check_distributions(self):
        """Validate statistical distributions"""
        self._log_section("4. Distribution Validation")

        total_entries = ContainerEntry.objects.count()
        if total_entries == 0:
            self._add_issue("No container entries found!")
            return

        # Status distribution (target: 70% EMPTY, 30% LADEN)
        status_stats = ContainerEntry.objects.values("status").annotate(count=Count("id"))
        status_dict = {item["status"]: item["count"] for item in status_stats}

        empty_count = status_dict.get("EMPTY", 0)
        laden_count = status_dict.get("LADEN", 0)

        empty_pct = (empty_count / total_entries) * 100
        laden_pct = (laden_count / total_entries) * 100

        self._log_item(f"Status: EMPTY {empty_pct:.1f}%, LADEN {laden_pct:.1f}%")

        if not (60 <= empty_pct <= 80):
            self._add_warning(f"EMPTY percentage {empty_pct:.1f}% outside target range (60-80%)")

        # Transport type distribution (target: 70% TRUCK, 30% TRAIN)
        transport_stats = ContainerEntry.objects.values("transport_type").annotate(count=Count("id"))
        transport_dict = {item["transport_type"]: item["count"] for item in transport_stats}

        truck_count = transport_dict.get("TRUCK", 0)
        train_count = transport_dict.get("TRAIN", 0)

        truck_pct = (truck_count / total_entries) * 100
        train_pct = (train_count / total_entries) * 100

        self._log_item(f"Transport: TRUCK {truck_pct:.1f}%, TRAIN {train_pct:.1f}%")

        if not (60 <= truck_pct <= 80):
            self._add_warning(f"TRUCK percentage {truck_pct:.1f}% outside target range (60-80%)")

        # Container size distribution (target: 70% 40ft, 30% 20ft)
        containers = ContainerEntry.objects.select_related("container").all()
        size_40ft = 0
        size_20ft = 0

        for entry in containers:
            iso_type = entry.container.iso_type
            if iso_type:
                size_code = iso_type[0]
                if size_code in ["4", "L"]:
                    size_40ft += 1
                else:
                    size_20ft += 1

        if total_entries > 0:
            size_40ft_pct = (size_40ft / total_entries) * 100
            size_20ft_pct = (size_20ft / total_entries) * 100

            self._log_item(f"Size: 40ft {size_40ft_pct:.1f}%, 20ft {size_20ft_pct:.1f}%")

            if not (60 <= size_40ft_pct <= 80):
                self._add_warning(f"40ft percentage {size_40ft_pct:.1f}% outside target range (60-80%)")

        # Work order success rate (target: 90% success, 5% fail, 5% pending)
        wo_stats = WorkOrder.objects.values("status").annotate(count=Count("id"))
        wo_dict = {item["status"]: item["count"] for item in wo_stats}
        total_wo = WorkOrder.objects.count()

        if total_wo > 0:
            success_count = wo_dict.get("VERIFIED", 0) + wo_dict.get("COMPLETED", 0)
            fail_count = wo_dict.get("FAILED", 0)
            pending_count = total_wo - success_count - fail_count

            success_pct = (success_count / total_wo) * 100
            fail_pct = (fail_count / total_wo) * 100
            pending_pct = (pending_count / total_wo) * 100

            self._log_item(
                f"Work Orders: Success {success_pct:.1f}%, "
                f"Failed {fail_pct:.1f}%, Pending {pending_pct:.1f}%"
            )

        # Pre-order coverage (target: 70% of entries have pre-orders)
        preorder_count = PreOrder.objects.count()
        preorder_pct = (preorder_count / total_entries) * 100 if total_entries > 0 else 0

        self._log_item(f"Pre-orders: {preorder_pct:.1f}% of entries")

        if not (60 <= preorder_pct <= 80):
            self._add_warning(f"Pre-order percentage {preorder_pct:.1f}% outside target range (60-80%)")

        self._log_pass("Distribution check complete")

    def _check_occupancy_consistency(self):
        """Validate occupancy grid consistency"""
        self._log_section("5. Occupancy Grid Consistency")

        issues_found = 0

        # Get all active positions (containers not exited)
        active_positions = ContainerPosition.objects.filter(
            container_entry__exit_date__isnull=True
        ).select_related("container_entry")

        # Check for duplicate positions
        position_counts = defaultdict(int)
        for position in active_positions:
            key = (position.zone, position.row, position.bay, position.tier, position.sub_slot)
            position_counts[key] += 1

        duplicates = {k: v for k, v in position_counts.items() if v > 1}
        if duplicates:
            for coords, count in duplicates.items():
                self._add_issue(
                    f"Duplicate position {coords}: {count} containers occupying same space"
                )
                issues_found += len(duplicates)

        # Check for positions without entries
        positions_without_entry = ContainerPosition.objects.filter(
            container_entry__isnull=True
        ).count()

        if positions_without_entry > 0:
            self._add_issue(f"Found {positions_without_entry} positions without container entry")
            issues_found += positions_without_entry

        # Check for exited containers still having positions
        exited_with_positions = ContainerEntry.objects.filter(
            exit_date__isnull=False,
            position__isnull=False,
        ).count()

        if exited_with_positions > 0:
            self._add_issue(f"Found {exited_with_positions} exited containers still having positions")
            issues_found += exited_with_positions

        if issues_found == 0:
            self._log_pass("Occupancy grid consistent")
        else:
            self._log_fail(f"Found {issues_found} occupancy issues")

    def _check_audit_trails(self):
        """Validate complete audit trails"""
        self._log_section("6. Audit Trail Validation")

        issues_found = 0

        # Check: Entries on terminal should have work orders
        entries_on_terminal = ContainerEntry.objects.filter(exit_date__isnull=True).count()
        entries_with_wo = ContainerEntry.objects.filter(
            exit_date__isnull=True,
            work_orders__isnull=False,
        ).distinct().count()

        coverage_pct = (entries_with_wo / entries_on_terminal * 100) if entries_on_terminal > 0 else 0
        self._log_item(f"Work order coverage: {coverage_pct:.1f}% of active entries")

        if coverage_pct < 80:
            self._add_warning(f"Low work order coverage: {coverage_pct:.1f}% (expected >80%)")

        # Check: Successful work orders should have positions
        successful_wo = WorkOrder.objects.filter(
            status__in=["COMPLETED", "VERIFIED"]
        ).count()

        wo_with_positions = WorkOrder.objects.filter(
            status__in=["COMPLETED", "VERIFIED"],
            container_entry__position__isnull=False,
        ).distinct().count()

        position_coverage = (wo_with_positions / successful_wo * 100) if successful_wo > 0 else 0
        self._log_item(f"Position coverage: {position_coverage:.1f}% of successful work orders")

        if position_coverage < 90:
            self._add_warning(f"Low position coverage: {position_coverage:.1f}% (expected >90%)")

        # Check: Container reuse
        from django.db.models import Count as DjangoCount
        reused_containers = ContainerEntry.objects.values("container").annotate(
            entry_count=DjangoCount("id")
        ).filter(entry_count__gt=1).count()

        total_containers = ContainerEntry.objects.values("container").distinct().count()
        reuse_pct = (reused_containers / total_containers * 100) if total_containers > 0 else 0

        self._log_item(f"Container reuse: {reuse_pct:.1f}% of containers used multiple times")

        if reuse_pct < 15:
            self._add_warning(f"Low container reuse: {reuse_pct:.1f}% (expected 20-30%)")

        self._log_pass("Audit trail check complete")

    def _add_issue(self, message: str):
        """Add critical issue"""
        self.issues.append(message)
        if self.verbosity >= 2:
            self.stdout.write(self.style.ERROR(f"  ✗ {message}"))

    def _add_warning(self, message: str):
        """Add warning"""
        self.warnings.append(message)
        if self.verbosity >= 2:
            self.stdout.write(self.style.WARNING(f"  ⚠ {message}"))

    def _log_section(self, title: str):
        """Log section header"""
        self.stdout.write(self.style.NOTICE(f"\n{title}"))

    def _log_item(self, message: str):
        """Log info item"""
        self.stdout.write(f"  ℹ {message}")

    def _log_pass(self, message: str):
        """Log passing check"""
        self.stdout.write(self.style.SUCCESS(f"  ✓ {message}"))

    def _log_fail(self, message: str):
        """Log failing check"""
        self.stdout.write(self.style.ERROR(f"  ✗ {message}"))

    def _print_summary(self):
        """Print verification summary"""
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("📋 VERIFICATION SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if len(self.issues) == 0 and len(self.warnings) == 0:
            self.stdout.write(self.style.SUCCESS("\n  ✅ ALL CHECKS PASSED!"))
            self.stdout.write(self.style.SUCCESS("  Data integrity verified successfully.\n"))
        else:
            if len(self.issues) > 0:
                self.stdout.write(self.style.ERROR(f"\n  ❌ CRITICAL ISSUES: {len(self.issues)}"))
                if self.verbosity < 2:
                    self.stdout.write("  Run with --verbose to see details")

            if len(self.warnings) > 0:
                self.stdout.write(self.style.WARNING(f"\n  ⚠️  WARNINGS: {len(self.warnings)}"))
                if self.verbosity < 2:
                    self.stdout.write("  Run with --verbose to see details")

            self.stdout.write(f"\n  Status: {'FAILED' if self.issues else 'PASSED WITH WARNINGS'}")

        self.stdout.write(self.style.SUCCESS("=" * 60 + "\n"))


# Import F for queryset comparisons
from django.db.models import F
