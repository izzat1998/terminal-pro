# MTT Container Terminal - Architecture Documentation

> **MTT** (Multi-modal Terminal Tracking) - A full-stack container terminal management system

## Table of Contents

- [System Overview](#system-overview)
- [System Context](#1-system-context-diagram)
- [Business Process Flow](#2-business-process-flow)
- [Container Entry Flow](#3-container-entry-sequence)
- [Customer Portal Flow](#4-customer-portal-sequence)
- [Data Model](#5-data-model-erd)
- [Component Architecture](#6-component-architecture)

---

## System Overview

MTT is a container terminal management system that enables:

| Actor | Access Method | Capabilities |
|-------|--------------|--------------|
| **Admin** | Web API | Full system access, user management |
| **Manager** | Telegram Bot | Container entry/exit, crane operations |
| **Customer** | Web Portal + Telegram | View containers, download documents, create pre-orders |

---

## 1. System Context Diagram

Shows **who** uses the system and **how** they interact with it.

```mermaid
flowchart TB
    subgraph Actors
        Admin["<b>Admin</b><br/>Full Access"]
        Manager["<b>Manager</b><br/>Terminal Staff"]
        Customer["<b>Customer</b><br/>Business Client"]
    end

    subgraph MTT["MTT Container Terminal System"]
        API["<b>Backend API</b><br/>Django DRF<br/>:8000/api"]
        Bot["<b>Telegram Bot</b><br/>aiogram 3.x"]
        Portal["<b>Customer Portal</b><br/>Vue 3 + TypeScript<br/>:5174"]
    end

    subgraph External["External Services"]
        TG["Telegram API"]
        PlateAPI["PlateRecognizer API"]
    end

    Admin -->|"REST API<br/>(JWT Auth)"| API
    Manager -->|"Telegram<br/>(Phone Auth)"| Bot
    Customer -->|"Web Browser<br/>(JWT Auth)"| Portal
    Customer -->|"Telegram<br/>(Phone Auth)"| Bot

    Bot <-->|"Bot API"| TG
    Bot -->|"Plate Recognition"| PlateAPI
    Portal -->|"REST API"| API
    Bot -->|"Django ORM"| API
```

### Access Methods

| Actor | Authentication | Interface |
|-------|---------------|-----------|
| Admin | Username + Password (JWT) | REST API |
| Manager | Phone number (Telegram) | Telegram Bot |
| Customer | Username + Password (JWT) | Vue.js Portal |
| Customer | Phone number (Telegram) | Telegram Bot |

---

## 2. Business Process Flow

The complete **container lifecycle** from gate entry to exit.

```mermaid
flowchart TD
    subgraph Entry["<b>CONTAINER ENTRY</b>"]
        A1["Truck arrives<br/>at gate"] --> A2{"Manager scans<br/>via Telegram"}
        A2 --> A3["Enter container<br/>number"]
        A3 --> A4["Select ISO type"]
        A4 --> A5["Choose status<br/>LADEN / EMPTY"]
        A5 --> A6["Capture truck<br/>plate photo"]
        A6 --> A7{"Pre-order<br/>exists?"}
        A7 -->|"Yes"| A8["Match pre-order<br/>Notify customer"]
        A7 -->|"No"| A9["Create entry<br/>record"]
        A8 --> A9
    end

    subgraph Storage["<b>TERMINAL STORAGE</b>"]
        B1["Container<br/>in terminal"] --> B2{"Crane<br/>operations?"}
        B2 -->|"Yes"| B3["Record crane op<br/>via Telegram"]
        B3 --> B1
        B2 -->|"No"| B4{"Ready for<br/>exit?"}
    end

    subgraph Exit["<b>CONTAINER EXIT</b>"]
        C1["Manager scans<br/>exit via Telegram"] --> C2["Enter container<br/>number"]
        C2 --> C3["System finds<br/>active entry"]
        C3 --> C4["Record exit<br/>transport details"]
        C4 --> C5["Add exit photos<br/>(optional)"]
        C5 --> C6["Complete exit"]
    end

    subgraph CustomerView["<b>CUSTOMER PORTAL</b>"]
        D1["Customer<br/>logs in"] --> D2["View company<br/>containers"]
        D2 --> D3["Download<br/>documents"]
        D2 --> D4["Create<br/>pre-orders"]
        D4 --> D5["Wait for<br/>gate match"]
    end

    A9 --> B1
    B4 -->|"Yes"| C1
    C6 --> E["Container<br/>leaves terminal"]

    D5 -.->|"Matches at gate"| A7

    style Entry fill:#e1f5fe
    style Storage fill:#fff3e0
    style Exit fill:#e8f5e9
    style CustomerView fill:#f3e5f5
```

### Container States

| State | Description |
|-------|-------------|
| **Entry Created** | Container registered in system with entry details |
| **In Terminal** | Container stored, may have crane operations |
| **Exit Recorded** | Container has left terminal with exit details |

### Pre-order Matching Flow

1. Customer creates pre-order with truck plate number
2. When truck arrives, manager photographs plate
3. System auto-recognizes plate via PlateRecognizer API
4. If match found, pre-order status changes to `MATCHED`
5. Customer receives notification

---

## 3. Container Entry Sequence

Technical flow when a **manager enters a container** via Telegram.

```mermaid
sequenceDiagram
    autonumber
    participant M as Manager
    participant Bot as Telegram Bot
    participant DB as Database
    participant PR as PlateRecognizer API

    M->>Bot: /create (or click button)
    Bot->>Bot: Check manager access
    Bot->>M: "Enter container number"

    M->>Bot: HDMU6565958
    Bot->>DB: Validate format & check duplicates
    DB-->>Bot: OK (no duplicate today)

    Bot->>M: "Select ISO type" (keyboard)
    M->>Bot: 22G1 (20ft standard)

    Bot->>M: "Select status"
    M->>Bot: LADEN

    Bot->>M: "Select transport type"
    M->>Bot: TRUCK

    Bot->>M: "Send plate photo"
    M->>Bot: [photo of truck plate]

    Bot->>PR: Recognize plate
    PR-->>Bot: "01A123BC" (87% confidence)

    Bot->>DB: Check pre-orders for plate
    DB-->>Bot: PreOrder found!
    Bot->>M: "Pre-order match found!"

    Bot->>M: "Confirm entry?"
    M->>Bot: Yes, create

    Bot->>DB: Create ContainerEntry
    Bot->>DB: Update PreOrder status
    Bot->>DB: Attach photos
    DB-->>Bot: Entry #12345 created

    Bot->>M: "Entry created! ID: #12345"
```

### Entry Data Collected

| Field | Required | Source |
|-------|----------|--------|
| Container Number | Yes | Manual input |
| ISO Type | Yes | Keyboard selection |
| Container Owner | No | Keyboard selection |
| Status (LADEN/EMPTY) | Yes | Keyboard selection |
| Transport Type | Yes | Keyboard selection |
| Transport Number | Yes | Plate recognition or manual |
| Photos | No | Telegram photos |

---

## 4. Customer Portal Sequence

Flow when a **customer uses the web portal**.

```mermaid
sequenceDiagram
    autonumber
    participant C as Customer
    participant Portal as Vue Portal
    participant API as Django API
    participant DB as Database

    Note over C,DB: Authentication
    C->>Portal: Open login page
    C->>Portal: Enter username/password
    Portal->>API: POST /api/auth/login/
    API->>DB: Validate credentials
    DB-->>API: User (customer type)
    API-->>Portal: JWT tokens + user info
    Portal->>Portal: Store tokens in cookies

    Note over C,DB: View Containers
    C->>Portal: Navigate to "Containers"
    Portal->>API: GET /api/customer/containers/
    API->>DB: Filter by customer.company
    DB-->>API: Company containers
    API-->>Portal: Paginated list
    Portal->>C: Display container table

    Note over C,DB: Download Document
    C->>Portal: Click download on file
    Portal->>API: GET /api/files/{id}/
    API-->>Portal: File stream
    Portal->>C: Browser downloads file

    Note over C,DB: Create Pre-order
    C->>Portal: Open "New Pre-order"
    C->>Portal: Enter plate number
    Portal->>API: POST /api/customer/preorders/
    API->>DB: Create PreOrder (PENDING)
    DB-->>API: PreOrder created
    API-->>Portal: Success response
    Portal->>C: "Pre-order created"
```

### Customer Capabilities

| Feature | Description |
|---------|-------------|
| **View Containers** | See all containers belonging to their company |
| **Container Details** | View entry/exit info, photos, documents |
| **Download Files** | Download attached images, PDFs, documents |
| **Create Pre-orders** | Register expected truck arrivals |
| **Track Pre-orders** | Monitor status (PENDING → MATCHED → COMPLETED) |

---

## 5. Data Model (ERD)

Key entity relationships in the system.

```mermaid
erDiagram
    CustomUser ||--o| ManagerProfile : "has"
    CustomUser ||--o| CustomerProfile : "has"
    Company ||--o{ ManagerProfile : "employs"
    Company ||--o{ CustomerProfile : "has"
    Company ||--o{ ContainerEntry : "owns"

    Container ||--o{ ContainerEntry : "tracked in"
    ContainerOwner ||--o{ ContainerEntry : "owns"
    ContainerEntry ||--o{ CraneOperation : "has"
    ContainerEntry ||--o{ PreOrder : "matched to"
    ContainerEntry ||--o{ FileAttachment : "has"

    CustomUser ||--o{ PreOrder : "creates"
    PreOrder ||--o| VehicleEntry : "matched to"
    VehicleEntry ||--o{ File : "has photos"

    CustomUser {
        int id PK
        string username
        string user_type "admin|manager|customer"
        bool is_active
    }

    Company {
        int id PK
        string name
        string slug UK
        bool is_active
    }

    Container {
        int id PK
        string container_number UK "ISO format: 4 letters + 7 digits"
        string iso_type "22G1, 42G1, etc."
    }

    ContainerEntry {
        int id PK
        int container_id FK
        datetime entry_time
        string status "LADEN|EMPTY"
        string transport_type "TRUCK|WAGON"
        string transport_number
        datetime exit_date "null until exit"
        int recorded_by_id FK
        int company_id FK
    }

    PreOrder {
        int id PK
        int customer_id FK
        string plate_number
        string operation_type "LOAD|UNLOAD"
        string status "PENDING|MATCHED|COMPLETED|CANCELLED"
        int matched_entry_id FK
        datetime matched_at
    }

    CraneOperation {
        int id PK
        int container_entry_id FK
        datetime operation_date
    }
```

### Key Relationships

| Relationship | Description |
|--------------|-------------|
| **User → Profile** | CustomUser has either ManagerProfile or CustomerProfile |
| **Company → Users** | Company has many managers and customers |
| **Company → Entries** | Company owns container entries |
| **Container → Entries** | One container can have multiple entry/exit cycles |
| **Entry → PreOrder** | Pre-order matched to container entry at gate |
| **Entry → CraneOps** | Multiple crane operations per entry |

---

## 6. Component Architecture

Technical system components and their relationships.

```mermaid
flowchart TB
    subgraph Frontend["<b>Frontend</b><br/>Vue 3 + TypeScript"]
        Views["<b>Views</b><br/>17 page components"]
        Components["<b>Components</b><br/>11 reusable"]
        Services["<b>Services</b><br/>API integration"]
        Composables["<b>Composables</b><br/>useAuth, etc."]
    end

    subgraph Backend["<b>Backend</b><br/>Django 5.2 + DRF"]
        subgraph Apps["Django Apps"]
            accounts["<b>accounts</b><br/>users, auth"]
            containers["<b>containers</b><br/>master data"]
            terminal_ops["<b>terminal_operations</b><br/>entries, pre-orders"]
            vehicles["<b>vehicles</b><br/>gate operations"]
            files["<b>files</b><br/>file management"]
            customer_portal["<b>customer_portal</b><br/>customer API"]
            core["<b>core</b><br/>utilities"]
        end

        subgraph ServiceLayer["Service Layer"]
            EntryService["ContainerEntry<br/>Service"]
            PreOrderService["PreOrder<br/>Service"]
            GateMatchService["GateMatching<br/>Service"]
        end
    end

    subgraph TelegramBot["<b>Telegram Bot</b><br/>aiogram 3.x"]
        Handlers["<b>Handlers</b><br/>entry, exit, crane"]
        BotServices["<b>Bot Services</b><br/>entry, plate, notify"]
        FSM["<b>FSM States</b><br/>EntryForm, ExitForm"]
        Middleware["<b>Middleware</b><br/>access control"]
    end

    subgraph Storage["<b>Data Storage</b>"]
        PostgreSQL[("<b>PostgreSQL</b><br/>Primary DB")]
        Redis[("<b>Redis</b><br/>FSM State")]
        FileStorage[("<b>File Storage</b><br/>/media")]
    end

    Views --> Services
    Services -->|"REST API"| Apps
    Apps --> ServiceLayer
    ServiceLayer --> PostgreSQL

    Handlers --> BotServices
    BotServices --> ServiceLayer
    Middleware --> accounts
    FSM --> Redis

    files --> FileStorage

    style Frontend fill:#e3f2fd
    style Backend fill:#fff8e1
    style TelegramBot fill:#e8f5e9
    style Storage fill:#fce4ec
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Vue 3, TypeScript, Vite | Customer portal SPA |
| **UI Library** | Ant Design Vue | Component library |
| **Backend** | Django 5.2, DRF | REST API |
| **Telegram Bot** | aiogram 3.x | Manager interface |
| **Database** | PostgreSQL | Primary data store |
| **Cache/FSM** | Redis | Bot state management |
| **File Storage** | Local/S3 | Document storage |

### Service Layer Pattern

All business logic resides in the service layer (`apps/*/services/`):

```
apps/
├── accounts/services/
│   ├── customer_service.py
│   ├── manager_service.py
│   └── company_service.py
├── terminal_operations/services/
│   ├── container_entry_service.py
│   ├── preorder_service.py
│   └── gate_matching_service.py
└── telegram_bot/services/
    ├── entry_service.py
    └── notification_service.py
```

---

## API Endpoints Summary

### Authentication (`/api/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login/` | Login (username or phone) |
| POST | `/logout/` | Logout & blacklist token |
| POST | `/token/refresh/` | Refresh JWT token |
| GET | `/profile/` | Current user profile |

### Terminal Operations (`/api/terminal/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/entries/` | List containers (60+ filters) |
| POST | `/entries/` | Create container entry |
| PATCH | `/entries/{id}/` | Update entry |
| POST | `/entries/import_excel/` | Bulk import |
| GET | `/entries/export_excel/` | Export filtered |

### Customer Portal (`/api/customer/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/containers/` | Company containers |
| GET | `/preorders/` | Customer pre-orders |
| POST | `/preorders/` | Create pre-order |
| PATCH | `/preorders/{id}/` | Update pre-order |

---

## Quick Reference

### Container Number Format
- **ISO Standard**: 4 letters + 7 digits
- **Example**: `HDMU6565958`
- **Validation**: Auto-uppercase, format check

### Container Status
- `LADEN` - Contains cargo
- `EMPTY` - No cargo

### Transport Types
- `TRUCK` - Road transport
- `WAGON` - Rail transport

### Pre-order Status Flow
```
PENDING → MATCHED → COMPLETED
    ↓
CANCELLED
```

---

*Last updated: January 2026*
