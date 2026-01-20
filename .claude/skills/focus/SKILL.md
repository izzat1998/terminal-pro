---
name: focus
description: Use when working on frontend features to navigate components, services, composables and related backend APIs without manual file exploration
---

# Focus Mode - MTT Frontend Navigator

Interactive menu for navigating the MTT frontend codebase with related backend APIs.

## How to Use

When invoked, present the **Feature Areas Menu** below. User selects a number, you show that area's files.

## Feature Areas Menu

Present this menu to the user:

```
┌─────────────────────────────────────────────────┐
│            MTT Frontend Focus Mode              │
├─────────────────────────────────────────────────┤
│  1. Dashboard & Analytics                       │
│  2. Container Management                        │
│  3. Container Placement (3D Yard)               │
│  4. Work Orders                                 │
│  5. Vehicles (Gate Operations)                  │
│  6. Terminal Vehicles (Yard Equipment)          │
│  7. Billing & Tariffs                           │
│  8. Customer Portal                             │
│  9. Company Management                          │
│ 10. Managers & Auth                             │
│ 11. Telegram Integration                        │
├─────────────────────────────────────────────────┤
│  0. Show all areas overview                     │
└─────────────────────────────────────────────────┘
Select a number (1-11, or 0):
```

## Area Details

When user selects an area, show its files in this format:

### 1. Dashboard & Analytics

| Layer | Files |
|-------|-------|
| **Views** | `views/Dashboard.vue`, `views/ExecutiveDashboard.vue` |
| **Components** | `components/dashboard/KpiCard.vue`, `components/dashboard/DashboardChart.vue`, `components/dashboard/ChartCard.vue`, `components/YardStatsBar.vue` |
| **Services** | `services/executiveDashboardService.ts` |
| **Composables** | `composables/useExecutiveDashboard.ts` |
| **Backend** | `apps/terminal_operations/` → stats endpoints |

### 2. Container Management

| Layer | Files |
|-------|-------|
| **Views** | `views/Companies.vue`, `views/ContainerOwners.vue` |
| **Components** | `components/ContainerTable.vue`, `components/UpsertContainerModal.vue`, `components/Container3DModal.vue`, `components/ContainerLocationView.vue`, `components/ExcelUploadModal.vue`, `components/ExcelExportModal.vue` |
| **Backend** | `apps/containers/` |

### 3. Container Placement (3D Yard)

| Layer | Files |
|-------|-------|
| **Views** | `views/ContainerPlacement.vue` |
| **Components** | `components/TerminalLayout3D.vue`, `components/PlacementPanel.vue`, `components/UnplacedContainersList.vue`, `components/placement/PlacementSteps.vue`, `components/placement/PlacementActions.vue`, `components/placement/PlacementConfirmModal.vue`, `components/placement/PositionSuggestionCard.vue`, `components/placement/PositionAlternativeGrid.vue`, `components/placement/ManualPositionForm.vue`, `components/placement/ContainerInfoCard.vue` |
| **Services** | `services/placementService.ts` |
| **Composables** | `composables/use3DScene.ts`, `composables/useContainerMesh.ts`, `composables/useContainerTransform.ts`, `composables/usePlacementState.ts` |
| **Backend** | `apps/terminal_operations/` → `/api/terminal/placement/*` |
| **Endpoints** | `GET /layout/`, `POST /suggest/`, `POST /assign/`, `PATCH /{id}/move/`, `DELETE /{id}/remove/`, `GET /available/`, `GET /unplaced/` |

### 4. Work Orders

| Layer | Files |
|-------|-------|
| **Views** | `views/WorkOrdersPage.vue` |
| **Components** | `components/placement/WorkOrderTaskPanel.vue`, `components/placement/WorkOrderTaskCard.vue`, `components/placement/WorkOrderOptions.vue` |
| **Services** | `services/workOrderService.ts` |
| **Composables** | `composables/useWorkOrdersPage.ts`, `composables/useWorkOrderTasks.ts` |
| **Backend** | `apps/terminal_operations/` → `/api/terminal/work-orders/*` |
| **Endpoints** | `GET /`, `POST /`, `GET /pending/`, `POST /{id}/assign/` |

### 5. Vehicles (Gate Operations)

| Layer | Files |
|-------|-------|
| **Views** | `views/Vehicles.vue`, `views/VehiclesCustomers.vue` |
| **Components** | `components/VehicleExitModal.vue`, `components/SidebarVehicleStatus.vue` |
| **Services** | `services/vehicleExportService.ts` |
| **Composables** | `composables/useVehicleCreateForm.ts`, `composables/useVehicleStats.ts` |
| **Backend** | `apps/vehicles/` |

### 6. Terminal Vehicles (Yard Equipment)

| Layer | Files |
|-------|-------|
| **Views** | `views/TerminalVehicles.vue` |
| **Components** | `components/TerminalVehicleEditModal.vue` |
| **Services** | `services/terminalVehicleService.ts`, `services/terminalVehicleStatusService.ts` |
| **Composables** | `composables/useTerminalVehicleStatus.ts` |
| **Backend** | `apps/terminal_operations/` → `/api/terminal/terminal-vehicles/*` |

### 7. Billing & Tariffs

| Layer | Files |
|-------|-------|
| **Views** | `views/Tariffs.vue`, `views/customer/Billing.vue` |
| **Components** | `components/billing/CurrentCosts.vue`, `components/billing/MonthlyStatements.vue`, `components/StorageCostModal.vue` |
| **Services** | `services/tariffsService.ts` |
| **Composables** | `composables/useStorageCosts.ts` |
| **Backend** | `apps/billing/` |

### 8. Customer Portal

| Layer | Files |
|-------|-------|
| **Views** | `views/customer/Dashboard.vue`, `views/customer/Containers.vue`, `views/customer/PreOrders.vue`, `views/customer/Users.vue`, `views/customer/Settings.vue`, `views/customer/Billing.vue` |
| **Backend** | `apps/customer_portal/` → `/api/customer/*` |

### 9. Company Management

| Layer | Files |
|-------|-------|
| **Views** | `views/company/CompanyInfo.vue`, `views/company/CompanyOrders.vue`, `views/company/CompanyUsers.vue`, `views/company/CompanyContainers.vue`, `views/company/CompanySettings.vue` |
| **Components** | `components/CompanyCards.vue` |
| **Backend** | `apps/accounts/` (Company model) |

### 10. Managers & Auth

| Layer | Files |
|-------|-------|
| **Views** | `views/Managers.vue`, `views/LoginView.vue`, `views/UnauthorizedView.vue` |
| **Components** | `components/ManagerEditModal.vue` |
| **Services** | `services/userService.ts` |
| **Composables** | `composables/useAuth.ts` |
| **Backend** | `apps/accounts/` |

### 11. Telegram Integration

| Layer | Files |
|-------|-------|
| **Views** | `views/TelegramBotSettings.vue` |
| **Services** | `services/telegramActivityService.ts` |
| **Backend** | Telegram bot (separate service) |

## After Selection

After showing area details, ask:
1. **Read a file?** - Offer to read any file from the list
2. **See related backend?** - Show backend service/views for that area
3. **Back to menu?** - Return to main menu

## File Paths

All frontend paths are relative to: `frontend/src/`
All backend paths are relative to: `backend/`
