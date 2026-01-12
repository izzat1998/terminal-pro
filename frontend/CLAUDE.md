# CLAUDE.md - MTT Frontend

This file provides guidance to Claude Code (claude.ai/code) when working with the frontend codebase.

## Project Overview

Vue 3 + TypeScript SPA for the MTT Container Terminal Management System. Built with Vite (rolldown-vite) and Ant Design Vue for the UI component library.

## Commands

```bash
# Development
npm run dev          # Start dev server (port 5174)
npm run build        # Type check + production build
npm run preview      # Preview production build

# From project root (recommended)
make frontend        # Start frontend only
make dev             # Start frontend + backend
```

## Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Framework | Vue 3.5 | Composition API with `<script setup>` |
| Language | TypeScript 5.9 | Strict mode enabled |
| UI Library | Ant Design Vue 4.x | Globally registered |
| Build Tool | Vite 7.x (rolldown) | Fast HMR, ESBuild |
| HTTP Client | Axios | Configured in `src/services/` |
| Routing | Vue Router 4.x | File-based routes in `src/router/` |

## Architecture

### Directory Structure

```
src/
├── main.ts              # App entry, registers Ant Design globally
├── App.vue              # Root component (minimal wrapper)
├── assets/              # Static assets (images, fonts)
├── components/          # Reusable components
│   ├── AppLayout.vue    # Main layout with header/nav/footer
│   ├── ContainerTable.vue
│   ├── ContainerCreateModal.vue
│   └── ...
├── views/               # Page-level components (one per route)
│   ├── LoginView.vue
│   ├── Companies.vue
│   ├── Vehicles.vue
│   └── company/         # Customer portal views
├── router/              # Vue Router configuration
│   └── index.ts
├── services/            # API client services
│   └── api.ts           # Axios instance with interceptors
├── composables/         # Reusable composition functions
├── utils/               # Utility functions
└── config/              # Configuration files
```

### Data Flow

```
View Component (src/views/)
    │
    ▼ calls
Service (src/services/)
    │
    ▼ HTTP request
Backend API (localhost:8000/api)
    │
    ▼ response
Service transforms data
    │
    ▼ returns
View updates reactive state
    │
    ▼ triggers
Template re-renders
```

## Component Patterns

### View Components (`src/views/`)

Page-level components mapped to routes. One view per route.

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getContainers } from '@/services/containers'
import type { Container } from '@/types'

const containers = ref<Container[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    containers.value = await getContainers()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <a-spin :spinning="loading">
    <ContainerTable :data="containers" />
  </a-spin>
</template>
```

### Reusable Components (`src/components/`)

Shared UI components with typed props and events.

```vue
<script setup lang="ts">
interface Props {
  title: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  submit: [data: FormData]
  cancel: []
}>()

const handleSubmit = (data: FormData) => {
  emit('submit', data)
}
</script>
```

### Composables (`src/composables/`)

Extract reusable stateful logic.

```typescript
// src/composables/useContainers.ts
import { ref, computed } from 'vue'
import { getContainers } from '@/services/containers'
import type { Container } from '@/types'

export function useContainers() {
  const containers = ref<Container[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const ladenCount = computed(() =>
    containers.value.filter(c => c.status === 'LADEN').length
  )

  async function fetchContainers() {
    loading.value = true
    error.value = null
    try {
      containers.value = await getContainers()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load'
    } finally {
      loading.value = false
    }
  }

  return { containers, loading, error, ladenCount, fetchContainers }
}
```

## API Integration

### Service Layer (`src/services/`)

All API calls go through service functions. Never call axios directly from components.

```typescript
// src/services/api.ts
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' }
})

// JWT token interceptor
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Handle token refresh or redirect to login
    }
    return Promise.reject(error)
  }
)
```

```typescript
// src/services/containers.ts
import { api } from './api'
import type { Container, ContainerEntry } from '@/types'

export async function getContainers(): Promise<Container[]> {
  const { data } = await api.get('/customer/containers/')
  return data.results
}

export async function createEntry(entry: Partial<ContainerEntry>): Promise<ContainerEntry> {
  const { data } = await api.post('/terminal/entries/', entry)
  return data
}
```

### Response Handling

Backend returns standardized responses:

```typescript
// Success response
interface SuccessResponse<T> {
  success: true
  data: T
  message?: string
}

// Error response
interface ErrorResponse {
  success: false
  error: {
    code: string
    message: string
    details?: Record<string, string[]>
  }
  timestamp: string
}
```

## State Management

### Principle: Keep State Simple

- **Component-local state**: Use `ref()` and `reactive()` for component-specific data
- **Shared state**: Use composables for logic shared between components
- **No Vuex/Pinia**: Avoid global stores unless absolutely necessary

### Reactive State Patterns

```typescript
// Simple state
const count = ref(0)

// Object state
const form = reactive({
  name: '',
  email: '',
  company: null as Company | null
})

// Computed derived state
const isValid = computed(() =>
  form.name.length > 0 && form.email.includes('@')
)

// Watch for side effects
watch(() => form.company, (newCompany) => {
  if (newCompany) {
    fetchCompanyDetails(newCompany.id)
  }
})
```

## TypeScript Configuration

Strict mode enabled with these rules:
- `noUnusedLocals` - No unused variables
- `noUnusedParameters` - No unused function parameters
- `noFallthroughCasesInSwitch` - Require break in switch cases
- `noUncheckedSideEffectImports` - Check side-effect imports
- `erasableSyntaxOnly` - Use type-only imports

### Type Definitions

```typescript
// src/types/index.ts
export interface Container {
  id: number
  container_number: string
  container_type: '20GP' | '40GP' | '40HC'
  status: 'LADEN' | 'EMPTY'
}

export interface ContainerEntry extends Container {
  entry_time: string
  exit_date: string | null
  transport_type: 'TRUCK' | 'WAGON'
  transport_number: string
}
```

## Ant Design Vue Usage

### Global Registration

Ant Design Vue is registered globally in `main.ts`:

```typescript
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

app.use(Antd)
```

**Never import individual components** - they're available globally:

```vue
<!-- Correct: Use directly -->
<template>
  <a-button type="primary">Submit</a-button>
  <a-table :columns="columns" :data-source="data" />
</template>

<!-- Wrong: Don't import individually -->
<script setup>
import { Button, Table } from 'ant-design-vue' // Don't do this!
</script>
```

### Common Components

| Component | Use For |
|-----------|---------|
| `<a-table>` | Data tables with pagination, sorting, filtering |
| `<a-form>` | Forms with validation |
| `<a-modal>` | Dialogs and confirmation |
| `<a-button>` | Actions and navigation |
| `<a-spin>` | Loading states |
| `<a-message>` | Toast notifications |

### Form Pattern

```vue
<script setup lang="ts">
import { reactive } from 'vue'
import type { FormInstance } from 'ant-design-vue'

interface FormState {
  container_number: string
  status: 'LADEN' | 'EMPTY'
}

const formRef = ref<FormInstance>()
const formState = reactive<FormState>({
  container_number: '',
  status: 'LADEN'
})

const rules = {
  container_number: [
    { required: true, message: 'Container number is required' },
    { pattern: /^[A-Z]{4}\d{7}$/, message: 'Invalid ISO format' }
  ]
}

const handleSubmit = async () => {
  await formRef.value?.validate()
  // Submit logic
}
</script>

<template>
  <a-form ref="formRef" :model="formState" :rules="rules" layout="vertical">
    <a-form-item label="Container Number" name="container_number">
      <a-input v-model:value="formState.container_number" />
    </a-form-item>
    <a-form-item label="Status" name="status">
      <a-select v-model:value="formState.status">
        <a-select-option value="LADEN">Laden</a-select-option>
        <a-select-option value="EMPTY">Empty</a-select-option>
      </a-select>
    </a-form-item>
    <a-button type="primary" @click="handleSubmit">Submit</a-button>
  </a-form>
</template>
```

## AI Assistant Guidelines

### DO

- Use TypeScript strict mode - no `any` types
- Follow `<script setup lang="ts">` syntax exclusively
- Type all props with `defineProps<T>()`
- Type all emits with `defineEmits<T>()`
- Extract reusable logic to composables
- Use Ant Design Vue component patterns
- Keep components focused (single responsibility)
- Handle loading and error states in views

### NEVER

- Use Options API (`export default { data(), methods: {} }`)
- Skip TypeScript types or use `any`
- Import Ant Design components individually
- Store sensitive data in localStorage (except JWT tokens)
- Make API calls directly from components (use services)
- Use `var` - always `const` or `let`
- Mutate props directly
- Create deeply nested component hierarchies

### Code Style

```typescript
// Imports order
import { ref, computed, onMounted } from 'vue'  // 1. Vue
import { useRouter } from 'vue-router'           // 2. Vue ecosystem
import { message } from 'ant-design-vue'         // 3. UI library
import { getContainers } from '@/services'       // 4. Local services
import type { Container } from '@/types'         // 5. Types (type-only)

// Naming conventions
const containerList = ref<Container[]>([])       // camelCase for variables
const isLoading = ref(false)                     // boolean prefixed with is/has/can
const handleSubmit = () => {}                    // handlers prefixed with handle
const fetchData = async () => {}                 // async functions describe action
```

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| TypeScript errors on build | Type mismatches | Run `npm run build` to see all errors |
| API connection refused | Backend not running | Start with `make backend` or check port 8000 |
| Ant Design styles missing | CSS not imported | Ensure `ant-design-vue/dist/reset.css` in main.ts |
| Route not found | Missing route config | Add route in `src/router/index.ts` |
| Token not sent | Interceptor issue | Check `api.ts` interceptor and localStorage |
| Component not updating | Reactivity lost | Use `ref()` for primitives, `reactive()` for objects |
| `v-model` not working | Wrong syntax | Use `v-model:value` for Ant Design inputs |

## Testing

```bash
# Run tests (if configured)
npm run test

# Type check only
npm run type-check
```

### Component Testing Pattern

```typescript
import { mount } from '@vue/test-utils'
import ContainerTable from '@/components/ContainerTable.vue'

describe('ContainerTable', () => {
  it('renders container data', () => {
    const wrapper = mount(ContainerTable, {
      props: {
        data: [{ id: 1, container_number: 'HDMU6565958' }]
      }
    })
    expect(wrapper.text()).toContain('HDMU6565958')
  })
})
```

## Environment Variables

All env vars must be prefixed with `VITE_` to be exposed to the client:

```env
# .env or .env.local
VITE_API_BASE_URL=http://localhost:8000/api
```

Access in code:

```typescript
const apiUrl = import.meta.env.VITE_API_BASE_URL
```
