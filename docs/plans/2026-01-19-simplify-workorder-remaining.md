# Complete WorkOrder Simplification - Lightweight Plan

**Goal:** Finish remaining tasks 9-11 from the main plan

**Files:**
- `backend/apps/core/management/commands/generate_realistic_data_v2.py` - already modified, need to review & commit
- `frontend/src/components/placement/WorkOrderTaskCard.vue` - already modified, need to review & commit
- `frontend/src/views/WorkOrdersPage.vue` - already modified, need to review & commit
- `backend/apps/terminal_operations/migrations/` - create data migration for status conversion

**Steps:**
1. Review uncommitted changes for Task 9 (data generation) → verify it uses only PENDING/COMPLETED
2. Review frontend uncommitted changes → verify alignment with 2-status workflow
3. Create data migration to convert old statuses → ASSIGNED/ACCEPTED/IN_PROGRESS/VERIFIED → COMPLETED, FAILED → PENDING
4. Run backend tests → fix any failures
5. Run frontend build → fix any TypeScript errors
6. Commit all changes
