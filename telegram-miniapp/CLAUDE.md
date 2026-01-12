# CLAUDE.md - MTT Telegram Mini App

This file provides guidance to Claude Code (claude.ai/code) when working with the Telegram Mini App codebase.

## Project Overview

React 18 Telegram Mini App for terminal managers to perform vehicle operations directly within Telegram. This is a mobile-first interface designed for on-site gate operations.

## Commands

```bash
# Development
npm run dev          # Start dev server (port 5175)
npm run dev:https    # Start with HTTPS (required for camera on non-localhost)
npm run build        # Type check + production build
npm run preview      # Preview production build (port 1002)
npm run lint         # Run ESLint
npm run lint:fix     # Auto-fix lint issues

# From project root (recommended)
make telegram-miniapp  # Start this service only
make dev               # Start all services (backend + frontend + telegram-miniapp)
```

## Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Framework | React 18.3 | Functional components with hooks |
| Language | TypeScript 5.9 | Strict mode enabled |
| UI Library | antd-mobile 5.x | Mobile-optimized Ant Design |
| Telegram UI | @telegram-apps/telegram-ui | Official Telegram components |
| Build Tool | Vite 6.x | With React SWC plugin |
| Styling | Tailwind CSS 4.x | Utility-first CSS |
| State | React Context + hooks | No external state library |
| Routing | React Router 6.x | Hash-based routing |
| Telegram SDK | @tma.js/sdk-react 3.x | Mini App SDK integration |

## Architecture

### Directory Structure

```
src/
├── index.tsx              # App entry point
├── init.ts                # Telegram SDK initialization
├── mockEnv.ts             # Development mock for Telegram environment
├── index.css              # Global styles (Tailwind)
├── components/            # Reusable components
│   ├── App.tsx            # Router setup
│   ├── Root.tsx           # Error boundary + TON Connect
│   ├── Layout.tsx         # Main layout (NavBar, TabBar, access check)
│   ├── Page.tsx           # Page wrapper
│   ├── ErrorBoundary.tsx  # Error handling
│   └── CameraCapture/     # Camera component
├── pages/                 # Page components (one per route)
│   ├── IndexPage/         # Dashboard with statistics
│   ├── VehiclesPage/      # Vehicle list
│   ├── CameraPage/        # Add vehicle entry with plate recognition
│   ├── ExitEntryPage/     # Vehicle exit
│   ├── ExitByIdPage/      # Exit specific vehicle
│   └── CheckInPage/       # Vehicle check-in
├── contexts/              # React contexts
│   ├── CameraContext.tsx  # Global camera stream management
│   └── PageContext.tsx    # Page title management
├── hooks/                 # Custom hooks
│   ├── useCameraCapture.ts
│   └── useAntdMobileTheme.ts
├── navigation/
│   └── routes.tsx         # Route definitions
├── css/                   # CSS utilities
│   ├── bem.ts             # BEM naming helpers
│   └── classnames.ts      # Class name utilities
└── helpers/
    └── publicUrl.ts       # Asset URL helpers
```

### Data Flow

```
Page Component (src/pages/)
    │
    ▼ fetch via fetch()
Backend API (localhost:8000/api via Vite proxy)
    │
    ▼ JSON response
Page updates local state (useState/useReducer)
    │
    ▼ triggers
Component re-render
```

## Key Features

### 1. Dashboard (IndexPage)
- Real-time terminal statistics
- Vehicle counts by type (LIGHT/CARGO)
- Dwell time analytics
- Overstayer alerts
- 30-day activity trends

### 2. Vehicle Entry (CameraPage)
- Camera capture for vehicle photos
- **AI Plate Recognition** via `/api/terminal/plate-recognizer/recognize/`
- Hierarchical vehicle type selection
- Form submission with images

### 3. Vehicle List (VehiclesPage)
- Paginated infinite scroll
- Photo thumbnails with viewer
- Quick actions (Accept/Exit)
- Status filtering

### 4. Vehicle Exit (ExitEntryPage, ExitByIdPage)
- Exit photo capture
- Load status recording
- Plate verification

### 5. Check-in (CheckInPage)
- Vehicle acceptance workflow
- Photo confirmation

## API Integration

### Base URL Configuration

**Development:** API calls are proxied through Vite:
```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

**Production:** Set `VITE_API_BASE_URL` environment variable.

### Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/vehicles/statistics/` | GET | Dashboard statistics |
| `/api/vehicles/choices/` | GET | Dropdown options |
| `/api/vehicles/entries/` | GET/POST | List/create vehicle entries |
| `/api/vehicles/entries/{id}/` | GET | Vehicle details |
| `/api/terminal/plate-recognizer/recognize/` | POST | AI plate recognition |
| `/api/auth/managers/gate_access/` | GET | Check Telegram user access |

### Request Pattern

```typescript
// Typical API call pattern
const fetchData = async () => {
  try {
    const response = await fetch('/api/vehicles/statistics/')
    if (!response.ok) throw new Error('Failed to fetch')
    const data = await response.json()
    setStatistics(data)
  } catch (error) {
    Toast.show({ icon: 'fail', content: 'Ошибка загрузки' })
  }
}
```

## Telegram-Specific Considerations

### Access Control
The app verifies manager access via Telegram user ID in `Layout.tsx`:
```typescript
// Checks /api/auth/managers/gate_access/ with Telegram initData
```

### Theme Integration
Syncs with Telegram dark/light mode via `useAntdMobileTheme` hook.

### Development Without Telegram
The `mockEnv.ts` file provides a mock Telegram environment for local development. Enable with `import.meta.env.DEV`.

### Secure Context Requirements
Camera features require HTTPS or localhost. For HTTPS development:
```bash
npm run dev:https
```

## Component Patterns

### Page Component

```tsx
import { useEffect, useState } from 'react'
import { Page } from '@/components/Page'

export function ExamplePage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData().then(setData).finally(() => setLoading(false))
  }, [])

  return (
    <Page title="Example" loading={loading}>
      {/* Page content */}
    </Page>
  )
}
```

### Camera Usage

```tsx
import { useCamera } from '@/contexts/CameraContext'

function CameraComponent() {
  const { stream, startCamera, stopCamera } = useCamera()

  useEffect(() => {
    startCamera()
    return () => stopCamera()
  }, [])

  // Use stream with <video> element
}
```

## AI Assistant Guidelines

### DO
- Use TypeScript strict mode - no `any` types
- Use functional components with hooks
- Follow existing patterns for API calls
- Use antd-mobile components for mobile UI
- Handle loading and error states
- Use Tailwind for custom styling

### NEVER
- Use class components
- Skip error handling for API calls
- Bypass access control checks
- Store sensitive data in localStorage
- Use `var` - always `const` or `let`
- Ignore TypeScript errors

### Code Style

```typescript
// Import order
import { useState, useEffect } from 'react'          // 1. React
import { useNavigate } from 'react-router-dom'       // 2. React ecosystem
import { Toast, Button } from 'antd-mobile'          // 3. UI libraries
import { Page } from '@/components/Page'             // 4. Local components
import type { VehicleEntry } from '@/types'          // 5. Types

// Naming conventions
const vehicleList = useState<VehicleEntry[]>([])     // camelCase for variables
const isLoading = useState(false)                    // boolean: is/has/can prefix
const handleSubmit = () => {}                        // handlers: handle prefix
const fetchVehicles = async () => {}                 // async: action verb
```

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| Camera not working | Not HTTPS | Use `npm run dev:https` or localhost |
| API calls fail | Proxy not configured | Check `vite.config.ts` proxy settings |
| Telegram SDK errors | Not in Telegram | Enable mock environment for dev |
| Theme not syncing | Hook not used | Wrap with `useAntdMobileTheme` |
| Photos too large | No compression | Use JPEG 0.7 quality, max 1280px |

## Environment Variables

```env
# .env.local (development overrides)
VITE_API_BASE_URL=http://localhost:8000/api

# Enable HTTPS for camera (uses mkcert)
HTTPS=true
```

## Localization

The app uses **Uzbek (Cyrillic)** for UI text:
- Labels, buttons, and messages are in Uzbek
- Error messages: Uzbek
- API errors: May be in Russian (from backend)
