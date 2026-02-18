---
name: vue3-composition-patterns
description: Use when writing or modifying Vue 3 frontend code - covers script setup, httpClient, composables, Ant Design Vue, types, and utilities specific to this MTT codebase
---

# MTT Vue 3 Frontend Patterns

Quick reference for the actual patterns used in `frontend/src/`.

## Component Structure

**Always `<script setup lang="ts">`. No Options API. No `any`.**

```vue
<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { http } from '@/utils/httpClient'
import type { Container } from '@/types'

interface Props {
  containerId: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'submit', data: Container): void
}

const emit = defineEmits<Emits>()

const data = ref<Container | null>(null)
const formState = reactive({ name: '', status: '' })
const isValid = computed(() => formState.name.length > 0)

onMounted(async () => {
  data.value = await http.get<Container>(`/terminal/containers/${props.containerId}/`)
})
</script>

<template>
  <!-- template -->
</template>

<style scoped>
/* scoped styles */
</style>
```

## HTTP Client

**Custom fetch wrapper at `@/utils/httpClient.ts`. NOT axios.**

```typescript
import { http } from '@/utils/httpClient'

// GET
const containers = await http.get<Container[]>('/terminal/containers/')

// POST
const result = await http.post<Container>('/terminal/containers/', { container_number: 'ABCD1234567' })

// PUT / PATCH / DELETE
await http.patch<Container>(`/terminal/containers/${id}/`, { status: 'EXITED' })
await http.delete(`/terminal/containers/${id}/`)

// File upload
await http.upload<UploadResponse>('/terminal/import/', formData)
```

**Auth handling:**
- JWT stored in `localStorage` as `'access_token'` / `'refresh_token'`
- Auto-injected as `Authorization: Bearer {token}`
- Auto-refresh on 401 with request queue

**Error handling:**
```typescript
import { ApiError } from '@/types/api'

try {
  await http.post('/endpoint', data)
} catch (error) {
  if (error instanceof ApiError) {
    message.error(error.message)
    if (error.hasFieldErrors()) {
      const emailError = error.getFieldError('email')
    }
  }
}
```

## Composable Patterns

**Naming: `use{Feature}.ts`. Always return an object.**

### Data Fetching Composable

```typescript
import { ref, computed } from 'vue'
import { http } from '@/utils/httpClient'
import type { Container } from '@/types'

export function useContainers() {
  const data = ref<Container[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isEmpty = computed(() => data.value.length === 0)

  async function fetchData() {
    try {
      loading.value = true
      error.value = null
      data.value = await http.get<Container[]>('/terminal/containers/')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Error'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, isEmpty, fetchData }
}
```

### CRUD Table Composable

```typescript
import { useCrudTable } from '@/composables/useCrudTable'

// In component:
const { dataSource, loading, pagination, searchText, fetchData, handleTableChange, handleSearch } =
  useCrudTable<RawType, TableRecord>('/terminal/containers/', (item) => ({
    key: String(item.id),
    id: item.id,
    container_number: item.container_number,
    // ... transform for table display
  }))
```

### Modal Visibility Helper

```typescript
import { useModalVisibility } from '@/composables/useModalVisibility'

// Props: { open: boolean }, Emits: { 'update:open': boolean }
const visible = useModalVisibility(props, emit)
// Use with: <a-modal v-model:open="visible">
```

### Auth Composable

```typescript
import { useAuth } from '@/composables/useAuth'

const { user, isAuthenticated, login, logout, verifyCurrentToken } = useAuth()
```

## State Management

**No Pinia. No Vuex. Composables + localStorage.**

```typescript
// State lives in composables
const { user, isAuthenticated } = useAuth()

// Persistence via localStorage
import { getStorageItem, setStorageItem, removeStorageItem } from '@/utils/storage'
```

## Ant Design Vue

**Globally registered in `main.ts`. Never import individual components.**

### Form Pattern

```vue
<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance } from 'ant-design-vue'

const formRef = ref<FormInstance>()
const formState = reactive({ username: '', email: '' })
const rules = {
  username: [{ required: true, message: 'Обязательное поле' }],
  email: [{ type: 'email', message: 'Некорректный email' }]
}

const handleSubmit = async () => {
  await formRef.value?.validate()
  // submit...
}
</script>

<template>
  <a-form ref="formRef" :model="formState" :rules="rules" layout="vertical">
    <a-form-item label="Username" name="username">
      <a-input v-model:value="formState.username" />
    </a-form-item>
    <a-button type="primary" @click="handleSubmit">Submit</a-button>
  </a-form>
</template>
```

### Table Pattern

```vue
<a-table
  :columns="columns"
  :data-source="dataSource"
  :loading="loading"
  :pagination="pagination"
  row-key="key"
  @change="handleTableChange"
>
  <template #bodyCell="{ column, record }">
    <template v-if="column.key === 'actions'">
      <a-space>
        <a-button type="link" size="small" @click="handleEdit(record)">Edit</a-button>
        <a-popconfirm title="Удалить?" @confirm="handleDelete(record.id)">
          <a-button type="link" danger size="small">Delete</a-button>
        </a-popconfirm>
      </a-space>
    </template>
  </template>
</a-table>
```

### Modal Pattern

```vue
<a-modal v-model:open="visible" title="Title" :confirm-loading="loading" @ok="handleSubmit">
  <!-- content -->
</a-modal>
```

### Common Components

```
<a-table>       <a-form>        <a-modal>       <a-button>
<a-input>       <a-select>      <a-switch>      <a-spin>
<a-card>        <a-tag>         <a-statistic>   <a-popconfirm>
<a-row>/<a-col> <a-alert>       <a-input-number> <a-input-password>
```

**Notifications:** `message.success('Done')`, `message.error('Failed')` from `ant-design-vue`

## Type Definitions

Located in `src/types/`. Always use explicit types.

```typescript
// src/types/api.ts
export interface ApiResponse<T> { success: true; data: T; message?: string }
export interface PaginatedResponse<T> { count: number; next: string | null; results: T[] }
export class ApiError extends Error { code: ApiErrorCode; fieldErrors: FieldErrors | null }

// src/types/vehicle.ts - entity types
export interface Vehicle { id: number; license_plate: string; status: string; ... }

// Table display types (transformed)
export interface VehicleRecord { key: string; id: number; license_plate: string; ... }
```

## Utilities

```typescript
// Date formatting (dayjs, Asia/Tashkent timezone)
import { formatDateTime, formatDate } from '@/utils/dateFormat'

// Currency
import { formatCurrency, formatUzs, formatCurrencyCompact } from '@/utils/formatters'
formatCurrency(1234.56, 'USD')   // '$1 234,56'
formatUzs('5000000')              // '5 000 000 сум'

// File download
import { downloadFile } from '@/utils/download'
await downloadFile('/api/export/containers/', 'containers.xlsx')

// Excel export (uses xlsx library)
import * as XLSX from 'xlsx'
```

## Import Order

```typescript
// 1. Vue core
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
// 2. UI library
import { message } from 'ant-design-vue'
// 3. Local utilities/services
import { http } from '@/utils/httpClient'
// 4. Types (type-only)
import type { Container } from '@/types'
```

## Router

```typescript
// Route meta typing
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
    roles?: ('admin' | 'customer')[]
  }
}

// Lazy-loaded routes
{ path: '/dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: 'Dashboard', roles: ['admin'] } }
```

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Variables | camelCase | `containerList`, `isLoading` |
| Booleans | is/has/can | `isLoading`, `hasError` |
| Components | PascalCase.vue | `ContainerTable.vue` |
| Composables | use + Feature | `useAuth.ts` |
| Services | feature + Service | `userService.ts` |
| Types | PascalCase | `Container`, `VehicleRecord` |

## Quick Checklist

- [ ] `<script setup lang="ts">` (no Options API)
- [ ] Props: `interface Props` + `withDefaults(defineProps<Props>(), {})`
- [ ] Emits: `interface Emits` + `defineEmits<Emits>()`
- [ ] No `any` types (strict mode)
- [ ] Use `http.get/post/patch/delete` (not axios)
- [ ] Ant Design components NOT imported (globally registered)
- [ ] User-facing text in Russian
- [ ] `ref<Type>()` with explicit generic
