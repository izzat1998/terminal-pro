---
name: focus
description: Set frontend section context for focused development. Use when working on specific pages/sections of the MTT frontend.
---

# Focus Skill - Frontend Section Navigator

Helps you focus on a specific section of the frontend by setting context and showing relevant files.

## When to Use This Skill

Claude should invoke this skill when:
- User types `/focus` or `/focus <section>`
- User wants to work on a specific frontend section
- User mentions multiple areas and needs to clarify which one

## Usage

```bash
/focus              # Show interactive picker
/focus containers   # Jump directly to Containers section
/focus placement    # Jump to 3D Terminal section
```

## Available Sections

When this skill is invoked, present the user with these options if no section is specified:

### Section Map

| Section Key | Display Name | Description |
|-------------|--------------|-------------|
| `containers` | 📦 Containers | Container entry/exit management |
| `placement` | 🎮 3D Terminal | Three.js 3D yard visualization |
| `gate` | 🚛 Gate (КПП) | Vehicle gate operations |
| `companies` | 🏢 Companies | Company management & details |
| `owners` | 👤 Container Owners | Container owner directory |
| `managers` | 👥 Managers | Terminal manager settings |
| `customers` | 🛒 Customer Portal | Customer-facing views |
| `telegram` | 🤖 Telegram Bot | Bot settings & integration |

---

## Section Details

### 📦 containers
**Container Management - Entry/Exit Tracking**

**Key Files:**
- `frontend/src/components/ContainerTable.vue` - Main table component
- `frontend/src/components/UpsertContainerModal.vue` - Add/edit container modal
- `frontend/src/components/ExcelUploadModal.vue` - Bulk import from Excel
- `frontend/src/components/ExcelExportModal.vue` - Export to Excel
- `frontend/src/components/FilesDialog.vue` - File attachments viewer
- `frontend/src/composables/useCrudTable.ts` - CRUD operations helper
- `frontend/src/composables/useContainerTransform.ts` - Data transformations

**Backend API:** `/api/terminal/entries/`

**Route:** `/containers`

---

### 🎮 placement
**3D Terminal Layout - Container Yard Visualization**

**Key Files:**
- `frontend/src/views/ContainerPlacement.vue` - Main placement view
- `frontend/src/components/PlacementPanel.vue` - Side panel controls
- `frontend/src/components/TerminalLayout3D.vue` - Three.js canvas
- `frontend/src/composables/use3DScene.ts` - Three.js scene setup
- `frontend/src/composables/useContainerMesh.ts` - Container mesh rendering
- `frontend/src/composables/usePlacementState.ts` - Placement state management
- `frontend/src/composables/useDuplicateCheck.ts` - Duplicate detection
- `frontend/src/services/placementService.ts` - Placement API calls
- `frontend/src/types/placement.ts` - TypeScript types

**Backend API:** `/api/terminal/placement/`

**Backend Service:** `backend/apps/terminal_operations/services/placement_service.py`

**Route:** `/placement`

---

### 🚛 gate
**Gate Operations (КПП) - Vehicle Entry/Exit**

**Key Files:**
- `frontend/src/views/Vehicles.vue` - Vehicle gate view
- `frontend/src/components/ContainerTable.vue` - Shared table component
- `backend/apps/vehicles/views.py` - Vehicle API views
- `backend/apps/vehicles/models.py` - Vehicle models

**Backend API:** `/api/vehicles/`

**Route:** `/gate`

---

### 🏢 companies
**Company Management - Client Organizations**

**Key Files:**
- `frontend/src/views/Companies.vue` - Company list view
- `frontend/src/layouts/CompanyLayout.vue` - Company detail layout (tabs)
- `frontend/src/views/company/CompanyInfo.vue` - Company info tab
- `frontend/src/views/company/CompanyUsers.vue` - Company users tab
- `frontend/src/views/company/CompanyOrders.vue` - Company orders tab
- `frontend/src/views/company/CompanyContainers.vue` - Company containers tab
- `frontend/src/views/company/CompanySettings.vue` - Company settings tab

**Backend API:** `/api/auth/companies/`

**Routes:** `/accounts/companies`, `/accounts/companies/:slug/*`

---

### 👤 owners
**Container Owners Directory**

**Key Files:**
- `frontend/src/views/ContainerOwners.vue` - Owner list view
- `frontend/src/composables/useCrudTable.ts` - CRUD operations

**Backend API:** `/api/terminal/owners/`

**Route:** `/owners`

---

### 👥 managers
**Terminal Managers - Staff Management**

**Key Files:**
- `frontend/src/views/Managers.vue` - Manager list view
- `frontend/src/components/ManagerEditModal.vue` - Edit manager modal

**Backend API:** `/api/auth/managers/`

**Route:** `/managers`

---

### 🛒 customers
**Customer Portal - Client-Facing Views**

**Key Files:**
- `frontend/src/layouts/CustomerLayout.vue` - Customer portal layout
- `frontend/src/views/customer/Dashboard.vue` - Customer dashboard
- `frontend/src/views/customer/Containers.vue` - Customer containers view
- `frontend/src/views/customer/PreOrders.vue` - Customer orders/preorders
- `frontend/src/views/customer/Users.vue` - Customer user management

**Backend API:** `/api/customer/`

**Routes:** `/customer/*`

---

### 🤖 telegram
**Telegram Bot Settings**

**Key Files:**
- `frontend/src/views/TelegramBotSettings.vue` - Bot configuration view
- `frontend/src/services/telegramActivityService.ts` - Activity logging

**Backend:** `backend/apps/telegram_bot/`

**Route:** `/telegram-bot`

---

## Instructions for Claude

When this skill is invoked:

1. **If no section specified:** Present an interactive picker using `AskUserQuestion` tool:
   ```
   Which frontend section do you want to focus on?
   ○ containers - Container entry/exit management
   ○ placement - 3D Terminal yard visualization
   ○ gate - Vehicle gate operations (КПП)
   ○ companies - Company management
   ○ owners - Container owners directory
   ○ managers - Terminal manager settings
   ○ customers - Customer portal views
   ○ telegram - Telegram bot settings
   ```

2. **If section specified:** Display the section details immediately

3. **After selection:**
   - Show the relevant files for that section
   - Confirm context is set: "✅ Context set to [Section]. I'll focus on these files."
   - Remember this context for subsequent questions in the conversation

4. **Context behavior:**
   - When user asks questions, prioritize files from the focused section
   - If question seems unrelated, ask if they want to switch sections
   - User can always run `/focus` again to change sections
