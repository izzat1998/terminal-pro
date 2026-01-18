# MTT Container Terminal - Improvement Plan

*Generated from 3-agent architecture review on 2026-01-18*

## Overview

| Metric | Current | Target |
|--------|---------|--------|
| Backend Score | 8.2/10 | 9.0/10 |
| Frontend Score | 8.5/10 | 9.5/10 |
| Mini App Score | 8.2/10 | 9.0/10 |
| **Overall** | **8.3/10** | **9.2/10** |

---

## Phase 1: Critical Fixes (Week 1)

### 🔴 PARALLEL STREAM A: Frontend TypeScript Fixes
**Agent Type:** Engineer
**Estimated Time:** 2-3 hours
**Dependencies:** None

**Tasks:**
1. Fix `priorityConfig` nullability in `WorkOrderTaskCard.vue` (line 96, 98)
2. Remove unused `watch` import in `WorkOrderTaskPanel.vue` (line 10)
3. Fix function signature mismatch in `ContainerPlacement.vue` (line 125)
4. Run `npx vue-tsc -b` to verify all errors resolved

**Acceptance Criteria:**
- [ ] `npm run build` passes without TypeScript errors
- [ ] All 4 compilation errors resolved

---

### 🔴 PARALLEL STREAM B: Backend Profile Migration
**Agent Type:** Engineer
**Estimated Time:** 4-6 hours
**Dependencies:** None

**Tasks:**
1. Create data migration to populate `ManagerProfile` from legacy `CustomUser` fields
2. Create data migration to populate `CustomerProfile` from legacy `CustomUser` fields
3. Update all code references from `user.phone_number` to `user.profile_phone_number`
4. Remove 7 legacy fields from `CustomUser` model
5. Update serializers to use profile data

**Files to Modify:**
- `backend/apps/accounts/models.py`
- `backend/apps/accounts/migrations/` (new migration)
- `backend/apps/accounts/serializers.py`
- All files using legacy user fields

**Acceptance Criteria:**
- [ ] All legacy fields removed from `CustomUser`
- [ ] All tests pass
- [ ] Data migration is reversible

---

### 🔴 PARALLEL STREAM C: Add Vite Alias Configuration
**Agent Type:** Engineer (Haiku)
**Estimated Time:** 30 minutes
**Dependencies:** None

**Tasks:**
1. Add `@/` path alias to `frontend/vite.config.ts`
2. Verify existing imports work correctly

**Code:**
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

**Acceptance Criteria:**
- [ ] `@/` imports resolve correctly
- [ ] Build passes

---

## Phase 2: Testing Infrastructure (Week 1-2)

### 🟠 PARALLEL STREAM D: Backend Test Enhancement
**Agent Type:** Engineer
**Estimated Time:** 1 day
**Dependencies:** Stream B (profile migration)

**Tasks:**
1. Add coverage reporting to pytest configuration
2. Add tests for `CraneOperationService`
3. Add tests for `WorkOrderService`
4. Add tests for `ExecutiveDashboardService`
5. Achieve 80%+ coverage on services/

**Files to Create:**
- `backend/tests/test_crane_operations.py`
- `backend/tests/test_executive_dashboard.py`
- `backend/pytest.ini` (coverage config)

**Acceptance Criteria:**
- [ ] Coverage report generated on `pytest --cov`
- [ ] Services have 80%+ coverage

---

### 🟠 PARALLEL STREAM E: Frontend Composable Tests
**Agent Type:** Engineer
**Estimated Time:** 1 day
**Dependencies:** Stream A (TS fixes)

**Tasks:**
1. Set up Vitest configuration
2. Add tests for `useAuth` composable
3. Add tests for `usePlacementState` composable
4. Add tests for `useCrudTable` composable
5. Add tests for `httpClient` token refresh logic

**Files to Create:**
- `frontend/vitest.config.ts`
- `frontend/src/composables/__tests__/useAuth.test.ts`
- `frontend/src/composables/__tests__/usePlacementState.test.ts`
- `frontend/src/composables/__tests__/useCrudTable.test.ts`
- `frontend/src/utils/__tests__/httpClient.test.ts`

**Acceptance Criteria:**
- [ ] `npm run test` runs successfully
- [ ] Critical composables have 80%+ coverage

---

### 🟠 PARALLEL STREAM F: Mini App Test Setup
**Agent Type:** Engineer
**Estimated Time:** 1 day
**Dependencies:** None

**Tasks:**
1. Configure Vitest for React
2. Add tests for `CameraContext` (stream reuse, cleanup)
3. Add tests for vehicle type selection logic
4. Add tests for API error handling
5. Add mock for Telegram SDK

**Files to Create:**
- `telegram-miniapp/vitest.config.ts`
- `telegram-miniapp/src/contexts/__tests__/CameraContext.test.tsx`
- `telegram-miniapp/src/pages/__tests__/CameraPage.test.tsx`
- `telegram-miniapp/src/__mocks__/telegram-sdk.ts`

**Acceptance Criteria:**
- [ ] `npm run test` runs successfully
- [ ] Camera context fully tested

---

## Phase 3: Robustness (Week 2)

### 🟡 PARALLEL STREAM G: Mini App Offline Support
**Agent Type:** Engineer
**Estimated Time:** 4-6 hours
**Dependencies:** Stream F (tests)

**Tasks:**
1. Add network status detection hook
2. Add offline indicator UI component
3. Implement LocalStorage caching for recent data
4. Add retry queue for failed submissions
5. Add service worker for basic offline caching

**Files to Create:**
- `telegram-miniapp/src/hooks/useNetworkStatus.ts`
- `telegram-miniapp/src/components/OfflineIndicator.tsx`
- `telegram-miniapp/src/utils/offlineStorage.ts`
- `telegram-miniapp/src/utils/retryQueue.ts`

**Acceptance Criteria:**
- [ ] App shows offline indicator when disconnected
- [ ] Recent data viewable offline
- [ ] Failed submissions retry when online

---

### 🟡 PARALLEL STREAM H: Backend Request Logging
**Agent Type:** Engineer
**Estimated Time:** 3-4 hours
**Dependencies:** None

**Tasks:**
1. Create request logging middleware
2. Log: user, endpoint, method, status code, duration
3. Use structured JSON logging for production
4. Add audit log model for persistent storage
5. Configure log rotation

**Files to Create:**
- `backend/apps/core/middleware/request_logging.py`
- `backend/apps/core/models/audit_log.py`

**Acceptance Criteria:**
- [ ] All API requests logged
- [ ] Logs queryable by user/endpoint
- [ ] No performance degradation (< 5ms overhead)

---

### 🟡 PARALLEL STREAM I: Backend N+1 Query Optimization
**Agent Type:** Engineer
**Estimated Time:** 3-4 hours
**Dependencies:** None

**Tasks:**
1. Install Django Debug Toolbar for development
2. Audit `ContainerEntryViewSet` queryset
3. Add `select_related()` for foreign keys
4. Add `prefetch_related()` for reverse relations
5. Verify with EXPLAIN ANALYZE

**Files to Modify:**
- `backend/terminal_app/settings.py` (debug toolbar)
- `backend/apps/terminal_operations/views.py`
- `backend/apps/vehicles/views.py`

**Acceptance Criteria:**
- [ ] No N+1 queries in container list view
- [ ] Query count < 5 for paginated list

---

## Phase 4: Polish (Week 3)

### 🟢 PARALLEL STREAM J: i18n Framework (Backend)
**Agent Type:** Engineer
**Estimated Time:** 1 day
**Dependencies:** None

**Tasks:**
1. Configure Django i18n settings
2. Wrap all user-facing strings with `gettext_lazy()`
3. Extract strings to `.po` files
4. Create Russian and Uzbek translations
5. Add language selection to API

**Acceptance Criteria:**
- [ ] All error messages translatable
- [ ] Russian and Uzbek `.po` files complete

---

### 🟢 PARALLEL STREAM K: i18n Framework (Mini App)
**Agent Type:** Engineer
**Estimated Time:** 4-6 hours
**Dependencies:** None

**Tasks:**
1. Create i18n utility with Uzbek/Russian support
2. Replace all hardcoded Uzbek strings
3. Replace all hardcoded Russian strings
4. Add language detection from Telegram settings

**Files to Create:**
- `telegram-miniapp/src/utils/i18n.ts`
- `telegram-miniapp/src/locales/uz.ts`
- `telegram-miniapp/src/locales/ru.ts`

**Acceptance Criteria:**
- [ ] All UI strings use i18n utility
- [ ] Language matches Telegram settings

---

### 🟢 PARALLEL STREAM L: Frontend Component Reorganization
**Agent Type:** Architect
**Estimated Time:** 2-3 hours
**Dependencies:** Stream A, E

**Tasks:**
1. Create feature-based folder structure
2. Move container components to `components/containers/`
3. Move common components to `components/common/`
4. Update all import paths
5. Verify build passes

**Target Structure:**
```
components/
├── common/          # AppLayout, FilesDialog, ExcelUploadModal
├── containers/      # ContainerTable, UpsertContainerModal
├── placement/       # (already organized)
├── dashboard/       # (already organized)
└── vehicles/        # VehicleTable, etc.
```

**Acceptance Criteria:**
- [ ] All components in feature folders
- [ ] No circular imports
- [ ] Build passes

---

### 🟢 PARALLEL STREAM M: E2E Testing Setup
**Agent Type:** QATester
**Estimated Time:** 1 day
**Dependencies:** Streams D, E, F

**Tasks:**
1. Configure Playwright for monorepo
2. Add E2E test for login flow
3. Add E2E test for container placement
4. Add E2E test for work order completion
5. Add CI integration

**Files to Create:**
- `e2e/playwright.config.ts`
- `e2e/tests/auth.spec.ts`
- `e2e/tests/container-placement.spec.ts`
- `e2e/tests/work-orders.spec.ts`

**Acceptance Criteria:**
- [ ] E2E tests run in CI
- [ ] Critical user flows covered

---

## Parallel Execution Matrix

```
Week 1:
┌─────────────────────────────────────────────────────────────────┐
│ Day 1-2:  [A: TS Fixes]  [B: Profile Migration]  [C: Vite Alias]│
│ Day 3-5:  [D: Backend Tests] [E: Frontend Tests] [F: Mini Tests]│
└─────────────────────────────────────────────────────────────────┘

Week 2:
┌─────────────────────────────────────────────────────────────────┐
│ Day 1-2:  [G: Offline Support] [H: Request Logging] [I: N+1 Fix]│
│ Day 3-5:  Continue D, E, F if needed                            │
└─────────────────────────────────────────────────────────────────┘

Week 3:
┌─────────────────────────────────────────────────────────────────┐
│ Day 1-3:  [J: i18n Backend] [K: i18n Mini App] [L: Reorganize]  │
│ Day 4-5:  [M: E2E Tests]                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Assignment Summary

| Stream | Agent Type | Model | Can Parallelize With |
|--------|------------|-------|---------------------|
| A | Engineer | Sonnet | B, C |
| B | Engineer | Sonnet | A, C |
| C | Engineer | Haiku | A, B |
| D | Engineer | Sonnet | E, F |
| E | Engineer | Sonnet | D, F |
| F | Engineer | Sonnet | D, E |
| G | Engineer | Sonnet | H, I |
| H | Engineer | Sonnet | G, I |
| I | Engineer | Sonnet | G, H |
| J | Engineer | Sonnet | K, L |
| K | Engineer | Sonnet | J, L |
| L | Architect | Sonnet | J, K |
| M | QATester | Sonnet | After D, E, F |

---

## Success Metrics

After completing all phases:

| Metric | Before | After |
|--------|--------|-------|
| TypeScript Errors | 4 | 0 |
| Backend Test Coverage | ~60% | 85%+ |
| Frontend Test Coverage | ~5% | 70%+ |
| Mini App Test Coverage | 0% | 70%+ |
| E2E Test Coverage | 0% | Critical flows |
| i18n Support | Partial | Full (uz/ru) |
| Offline Support | None | Basic |
| N+1 Queries | Present | Eliminated |

**Target Score: 9.2/10** 🎯
