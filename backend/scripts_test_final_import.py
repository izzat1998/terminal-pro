#!/usr/bin/env python
"""
Final comprehensive test of Excel import functionality
"""
import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'terminal_app.settings')
django.setup()

from apps.accounts.models import CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, ContainerOwner
from apps.terminal_operations.services.container_entry_import_service import (
    ContainerEntryImportService,
)


def test_import():
    print("=" * 70)
    print("FINAL COMPREHENSIVE TEST - Excel Import Functionality")
    print("=" * 70)

    # Get admin user
    user = CustomUser.objects.filter(is_superuser=True).first()
    if not user:
        print("ERROR: No admin user found")
        return False
    print(f"✓ User: {user.username}\n")

    # Check file exists
    file_path = 'EMPTY_cntr_IN_OUT Interrail Services AG.xlsx'
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return False
    print(f"✓ Excel file: {file_path}\n")

    # Initial state
    print("Initial Database State:")
    print(f"  - ContainerEntry: {ContainerEntry.objects.count()}")
    print(f"  - ContainerOwner: {ContainerOwner.objects.count()}")
    print(f"  - Container: {Container.objects.count()}\n")

    # Perform import
    print("Starting import...\n")
    service = ContainerEntryImportService()

    try:
        with open(file_path, 'rb') as f:
            result = service.import_from_excel(f, user)

        # Display results
        print("=" * 70)
        print("IMPORT RESULTS")
        print("=" * 70)
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}\n")

        stats = result.get('statistics', {})
        print("Statistics:")
        print(f"  - Total rows:        {stats.get('total_rows', 0)}")
        print(f"  - Successful:        {stats.get('successful', 0)}")
        print(f"  - Skipped:           {stats.get('skipped', 0)}")
        print(f"  - Failed:            {stats.get('failed', 0)}")
        print(f"  - Processing time:   {stats.get('processing_time_seconds', 0)}s\n")

        # Show errors if any
        errors = result.get('errors', [])
        if errors:
            print(f"❌ ERRORS FOUND ({len(errors)} total):")
            for i, error in enumerate(errors[:10], 1):
                print(f"  {i}. Row {error['row']}: {error['error']}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors\n")
        else:
            print("✓ No errors\n")

        # Final database state
        final_entries = ContainerEntry.objects.count()
        final_owners = ContainerOwner.objects.count()
        final_containers = Container.objects.count()

        print("Final Database State:")
        print(f"  - ContainerEntry: {final_entries}")
        print(f"  - ContainerOwner: {final_owners}")
        print(f"  - Container: {final_containers}\n")

        # Detailed verification
        print("=" * 70)
        print("VERIFICATION CHECKS")
        print("=" * 70)

        # Check 1: ContainerOwner records
        owners = ContainerOwner.objects.all()
        print(f"\n1. ContainerOwner Records ({owners.count()} total):")
        for owner in owners:
            count = ContainerEntry.objects.filter(container_owner=owner).count()
            print(f"   - {owner.name} (ID: {owner.id}, slug: {owner.slug})")
            print(f"     Entries using this owner: {count}")

        # Check 2: Sample entries with ContainerOwner
        print("\n2. Sample ContainerEntry Records with ContainerOwner:")
        sample_entries = ContainerEntry.objects.filter(container_owner__isnull=False)[:5]
        for entry in sample_entries:
            print(f"   - Container: {entry.container.container_number}")
            print(f"     Owner: {entry.container_owner.name} (Type: {type(entry.container_owner).__name__})")
            print(f"     Entry time: {entry.entry_time}")
            print(f"     Status: {entry.status}")

        # Check 3: Entries without owner
        entries_without_owner = ContainerEntry.objects.filter(container_owner__isnull=True).count()
        print(f"\n3. Entries without ContainerOwner: {entries_without_owner}")

        # Check 4: ForeignKey relationship integrity
        print("\n4. ForeignKey Relationship Test:")
        test_entry = ContainerEntry.objects.filter(container_owner__isnull=False).first()
        if test_entry:
            print(f"   - Entry ID: {test_entry.id}")
            print(f"   - Owner field type: {type(test_entry.container_owner)}")
            print(f"   - Owner name: {test_entry.container_owner.name}")
            print("   - Can access owner.name: ✓")
            print(f"   - Can access owner.slug: {test_entry.container_owner.slug}")
            print("   - ForeignKey working correctly: ✓")
        else:
            print("   ❌ No entries with ContainerOwner found")

        # Check 5: Expected vs Actual
        print("\n5. Data Validation:")
        expected_rows = 1307
        success_rate = (stats.get('successful', 0) / expected_rows * 100) if expected_rows > 0 else 0
        print(f"   - Expected rows: {expected_rows}")
        print(f"   - Successfully imported: {stats.get('successful', 0)}")
        print(f"   - Success rate: {success_rate:.1f}%")

        if success_rate == 100:
            print("   ✓ Perfect import!")
        elif success_rate >= 95:
            print("   ⚠ Good import (some errors)")
        else:
            print("   ❌ Many errors detected")

        # Final verdict
        print("\n" + "=" * 70)
        if result['success'] and stats.get('failed', 0) == 0:
            print("✅ TEST PASSED: Excel import working perfectly!")
            print("=" * 70)
            return True
        elif result['success'] and stats.get('failed', 0) < 50:
            print("⚠️  TEST PARTIAL: Import succeeded with some errors")
            print("=" * 70)
            return True
        else:
            print("❌ TEST FAILED: Import has significant issues")
            print("=" * 70)
            return False

    except Exception as e:
        print("\n❌ EXCEPTION during import:")
        print(f"   {e!s}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_import()
    exit(0 if success else 1)
