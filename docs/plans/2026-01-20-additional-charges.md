# Additional Charges Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add discrete, one-time charges (service fees, penalties, equipment charges) that can be applied to containers multiple times.

**Architecture:** New `AdditionalCharge` model linked to `ContainerEntry`, with full CRUD API for admins and read-only for customers. Charges integrate into `CurrentCosts.vue` as a separate table and appear in monthly statements.

**Tech Stack:** Django 5.2, DRF, Vue 3 + TypeScript, Ant Design Vue

---

## Task 1: Create AdditionalCharge Model

**Files:**
- Modify: `backend/apps/billing/models.py`

**Step 1: Add the AdditionalCharge model**

Add at the end of `backend/apps/billing/models.py`:

```python
class AdditionalCharge(TimestampedModel):
    """
    Discrete one-time charge applied to a container entry.

    Examples: crane usage, inspection fee, handling charge, penalties.
    Can be applied multiple times to the same container.
    """

    container_entry = models.ForeignKey(
        "terminal_operations.ContainerEntry",
        on_delete=models.CASCADE,
        related_name="additional_charges",
        verbose_name="Запись контейнера",
    )

    description = models.CharField(
        max_length=255,
        verbose_name="Описание",
        help_text="Описание услуги или сбора",
    )

    amount_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Сумма USD",
    )

    amount_uzs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Сумма UZS",
    )

    charge_date = models.DateField(
        verbose_name="Дата начисления",
        help_text="Дата, к которой относится начисление (для выписки)",
    )

    created_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_charges",
        verbose_name="Создано пользователем",
    )

    class Meta:
        verbose_name = "Дополнительное начисление"
        verbose_name_plural = "Дополнительные начисления"
        ordering = ["-charge_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["container_entry", "charge_date"],
                name="charge_entry_date_idx",
            ),
            models.Index(fields=["charge_date"], name="charge_date_idx"),
        ]

    def __str__(self):
        return f"{self.description} - ${self.amount_usd} ({self.container_entry.container.container_number})"
```

**Step 2: Create migration**

Run:
```bash
cd backend && python manage.py makemigrations billing -n add_additional_charge
```

**Step 3: Apply migration**

Run:
```bash
cd backend && python manage.py migrate
```

**Step 4: Commit**

```bash
git add backend/apps/billing/models.py backend/apps/billing/migrations/
git commit -m "feat(billing): add AdditionalCharge model for discrete charges"
```

---

## Task 2: Create AdditionalCharge Serializers

**Files:**
- Modify: `backend/apps/billing/serializers.py`

**Step 1: Add serializers**

Add at the end of `backend/apps/billing/serializers.py`:

```python
from .models import AdditionalCharge


class AdditionalChargeSerializer(serializers.ModelSerializer):
    """Serializer for reading additional charges."""

    created_by_name = serializers.SerializerMethodField()
    container_number = serializers.CharField(
        source="container_entry.container.container_number", read_only=True
    )
    company_name = serializers.CharField(
        source="container_entry.company.name", read_only=True
    )

    class Meta:
        model = AdditionalCharge
        fields = [
            "id",
            "container_entry",
            "container_number",
            "company_name",
            "description",
            "amount_usd",
            "amount_uzs",
            "charge_date",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]

    def get_created_by_name(self, obj) -> str:
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return ""


class AdditionalChargeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating additional charges."""

    class Meta:
        model = AdditionalCharge
        fields = [
            "container_entry",
            "description",
            "amount_usd",
            "amount_uzs",
            "charge_date",
        ]

    def validate_amount_usd(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        return value

    def validate_amount_uzs(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
```

**Step 2: Commit**

```bash
git add backend/apps/billing/serializers.py
git commit -m "feat(billing): add AdditionalCharge serializers"
```

---

## Task 3: Create AdditionalCharge API Views

**Files:**
- Modify: `backend/apps/billing/views.py`

**Step 1: Add imports at top of views.py**

Add to the imports section:

```python
from .models import Tariff, AdditionalCharge
from .serializers import (
    # ... existing imports ...
    AdditionalChargeSerializer,
    AdditionalChargeCreateSerializer,
)
```

**Step 2: Add AdditionalChargeViewSet**

Add after the existing viewsets:

```python
class AdditionalChargeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing additional charges (admin only).

    list: Get all additional charges (filterable)
    create: Create a new charge
    retrieve: Get a specific charge
    update: Update a charge
    destroy: Delete a charge
    """

    queryset = AdditionalCharge.objects.all().select_related(
        "container_entry__container",
        "container_entry__company",
        "created_by",
    )
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AdditionalChargeCreateSerializer
        return AdditionalChargeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by container entry
        container_entry_id = self.request.query_params.get("container_entry_id")
        if container_entry_id:
            queryset = queryset.filter(container_entry_id=container_entry_id)

        # Filter by company
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(container_entry__company_id=company_id)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(charge_date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(charge_date__lte=date_to)

        return queryset.order_by("-charge_date", "-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        charge = serializer.save()

        response_serializer = AdditionalChargeSerializer(charge)
        return Response(
            {"success": True, "data": response_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = AdditionalChargeSerializer(instance)
        return Response({"success": True, "data": response_serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"success": True, "message": "Начисление удалено"},
            status=status.HTTP_200_OK,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = AdditionalChargeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AdditionalChargeSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AdditionalChargeSerializer(instance)
        return Response({"success": True, "data": serializer.data})


class CustomerAdditionalChargeView(APIView):
    """
    Customer view for their additional charges (read-only).

    GET /api/customer/additional-charges/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get customer's company
        if hasattr(user, "customer_profile") and user.customer_profile.company:
            company = user.customer_profile.company
        elif user.company:
            company = user.company
        else:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "NO_COMPANY",
                        "message": "Пользователь не привязан к компании",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = AdditionalCharge.objects.filter(
            container_entry__company=company
        ).select_related(
            "container_entry__container",
            "container_entry__company",
            "created_by",
        ).order_by("-charge_date", "-created_at")

        # Filter by date range
        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(charge_date__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(charge_date__lte=date_to)

        # Search by container number
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                container_entry__container__container_number__icontains=search
            )

        # Calculate summary
        from django.db.models import Sum
        totals = queryset.aggregate(
            total_usd=Sum("amount_usd"),
            total_uzs=Sum("amount_uzs"),
        )

        serializer = AdditionalChargeSerializer(queryset, many=True)

        return Response({
            "success": True,
            "data": serializer.data,
            "summary": {
                "total_charges": queryset.count(),
                "total_usd": str(totals["total_usd"] or 0),
                "total_uzs": str(totals["total_uzs"] or 0),
            },
        })
```

**Step 3: Commit**

```bash
git add backend/apps/billing/views.py
git commit -m "feat(billing): add AdditionalCharge API views"
```

---

## Task 4: Register API URLs

**Files:**
- Modify: `backend/apps/billing/urls.py`

**Step 1: Update urls.py**

Replace the entire content of `backend/apps/billing/urls.py`:

```python
"""
URL configuration for billing app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdditionalChargeViewSet,
    BulkStorageCostView,
    CustomerAdditionalChargeView,
    CustomerStorageCostView,
    StorageCostView,
    TariffViewSet,
)


router = DefaultRouter()
router.register(r"tariffs", TariffViewSet, basename="tariff")
router.register(r"additional-charges", AdditionalChargeViewSet, basename="additional-charge")

urlpatterns = [
    # Tariff management (admin)
    path("", include(router.urls)),
    # Storage cost calculation
    path(
        "container-entries/<int:entry_id>/storage-cost/",
        StorageCostView.as_view(),
        name="container-storage-cost",
    ),
    path(
        "storage-costs/calculate/",
        BulkStorageCostView.as_view(),
        name="bulk-storage-cost",
    ),
]

# Customer portal URLs (to be included in customer_portal app)
customer_urlpatterns = [
    path(
        "storage-costs/",
        CustomerStorageCostView.as_view(),
        name="customer-storage-costs",
    ),
    path(
        "additional-charges/",
        CustomerAdditionalChargeView.as_view(),
        name="customer-additional-charges",
    ),
]
```

**Step 2: Add customer URL to customer_portal urls**

Check `backend/apps/customer_portal/urls.py` and add the additional-charges endpoint if not already included via `customer_urlpatterns`.

**Step 3: Commit**

```bash
git add backend/apps/billing/urls.py backend/apps/customer_portal/urls.py
git commit -m "feat(billing): register AdditionalCharge API URLs"
```

---

## Task 5: Create Frontend Service

**Files:**
- Create: `frontend/src/services/additionalChargesService.ts`

**Step 1: Create the service file**

```typescript
import { http } from '../utils/httpClient';

export interface AdditionalCharge {
  id: number;
  container_entry: number;
  container_number: string;
  company_name: string | null;
  description: string;
  amount_usd: string;
  amount_uzs: string;
  charge_date: string;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  created_by_name: string;
}

export interface AdditionalChargeCreateData {
  container_entry: number;
  description: string;
  amount_usd: number;
  amount_uzs: number;
  charge_date: string;
}

export interface AdditionalChargeSummary {
  total_charges: number;
  total_usd: string;
  total_uzs: string;
}

export interface AdditionalChargesResponse {
  success: boolean;
  data: AdditionalCharge[];
  summary: AdditionalChargeSummary;
}

class AdditionalChargesService {
  /**
   * Get additional charges for customer's company
   */
  async getCustomerCharges(params?: {
    date_from?: string;
    date_to?: string;
    search?: string;
  }): Promise<AdditionalChargesResponse> {
    const searchParams = new URLSearchParams();
    if (params?.date_from) searchParams.append('date_from', params.date_from);
    if (params?.date_to) searchParams.append('date_to', params.date_to);
    if (params?.search) searchParams.append('search', params.search);

    const query = searchParams.toString();
    const url = `/customer/additional-charges/${query ? '?' + query : ''}`;
    return http.get<AdditionalChargesResponse>(url);
  }

  /**
   * Get additional charges for a specific company (admin)
   */
  async getCompanyCharges(
    companySlug: string,
    params?: {
      date_from?: string;
      date_to?: string;
      search?: string;
    }
  ): Promise<AdditionalChargesResponse> {
    const searchParams = new URLSearchParams();
    if (params?.date_from) searchParams.append('date_from', params.date_from);
    if (params?.date_to) searchParams.append('date_to', params.date_to);
    if (params?.search) searchParams.append('search', params.search);

    const query = searchParams.toString();
    const url = `/auth/companies/${companySlug}/additional-charges/${query ? '?' + query : ''}`;
    return http.get<AdditionalChargesResponse>(url);
  }

  /**
   * Create a new additional charge (admin only)
   */
  async create(data: AdditionalChargeCreateData): Promise<{ success: boolean; data: AdditionalCharge }> {
    return http.post('/billing/additional-charges/', data);
  }

  /**
   * Update an additional charge (admin only)
   */
  async update(
    id: number,
    data: Partial<AdditionalChargeCreateData>
  ): Promise<{ success: boolean; data: AdditionalCharge }> {
    return http.patch(`/billing/additional-charges/${id}/`, data);
  }

  /**
   * Delete an additional charge (admin only)
   */
  async delete(id: number): Promise<{ success: boolean; message: string }> {
    return http.delete(`/billing/additional-charges/${id}/`);
  }
}

export const additionalChargesService = new AdditionalChargesService();
```

**Step 2: Commit**

```bash
git add frontend/src/services/additionalChargesService.ts
git commit -m "feat(frontend): add additionalChargesService"
```

---

## Task 6: Create AdditionalCharges Component

**Files:**
- Create: `frontend/src/components/billing/AdditionalCharges.vue`

**Step 1: Create the component**

```vue
<template>
  <div class="additional-charges">
    <!-- Header with search and add button -->
    <div class="header-actions">
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="Поиск по номеру контейнера"
          style="width: 250px"
          allow-clear
        />
        <a-button
          v-if="isAdmin"
          type="primary"
          @click="openAddModal"
        >
          <template #icon><PlusOutlined /></template>
          Добавить
        </a-button>
      </a-space>
    </div>

    <!-- Summary Statistics -->
    <a-row :gutter="[16, 16]" style="margin-bottom: 20px;">
      <a-col :xs="12" :sm="8">
        <a-statistic
          title="Всего начислений"
          :value="summary.total_charges"
          :value-style="{ color: '#1677ff' }"
        >
          <template #prefix><FileTextOutlined /></template>
        </a-statistic>
      </a-col>
      <a-col :xs="12" :sm="8">
        <a-statistic
          title="Итого (USD)"
          :value="formatCurrency(summary.total_usd, 'USD')"
          :value-style="{ color: '#52c41a' }"
        />
      </a-col>
      <a-col :xs="12" :sm="8">
        <a-statistic
          title="Итого (UZS)"
          :value="formatCurrency(summary.total_uzs, 'UZS')"
          :value-style="{ color: '#722ed1' }"
        />
      </a-col>
    </a-row>

    <a-divider style="margin: 12px 0;" />

    <!-- Filters -->
    <a-space wrap style="margin-bottom: 16px;">
      <a-range-picker
        v-model:value="dateRange"
        format="DD.MM.YYYY"
        :placeholder="['Дата с', 'Дата по']"
        style="width: 240px"
        @change="fetchCharges"
        allow-clear
      />
    </a-space>

    <a-empty v-if="!loading && charges.length === 0" description="Дополнительные начисления не найдены" />

    <a-table
      v-else
      :columns="columns"
      :data-source="charges"
      :loading="loading"
      row-key="id"
      :scroll="{ x: 1000 }"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'container'">
          <a-tag color="blue">{{ record.container_number }}</a-tag>
        </template>
        <template v-if="column.key === 'charge_date'">
          {{ formatDate(record.charge_date) }}
        </template>
        <template v-if="column.key === 'amount_usd'">
          <span class="amount-usd">${{ parseFloat(record.amount_usd).toFixed(2) }}</span>
        </template>
        <template v-if="column.key === 'amount_uzs'">
          <span class="amount-uzs">{{ formatUzs(record.amount_uzs) }}</span>
        </template>
        <template v-if="column.key === 'actions'">
          <a-space v-if="isAdmin">
            <a-tooltip title="Редактировать">
              <a-button type="link" size="small" @click="openEditModal(record)">
                <template #icon><EditOutlined /></template>
              </a-button>
            </a-tooltip>
            <a-popconfirm
              title="Удалить начисление?"
              ok-text="Да"
              cancel-text="Нет"
              @confirm="deleteCharge(record.id)"
            >
              <a-tooltip title="Удалить">
                <a-button type="link" size="small" danger>
                  <template #icon><DeleteOutlined /></template>
                </a-button>
              </a-tooltip>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- Add/Edit Modal -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingCharge ? 'Редактировать начисление' : 'Добавить начисление'"
      :confirm-loading="saving"
      @ok="handleSave"
      @cancel="closeModal"
    >
      <a-form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        layout="vertical"
      >
        <a-form-item label="Контейнер" name="container_entry" v-if="!editingCharge">
          <a-select
            v-model:value="formState.container_entry"
            show-search
            placeholder="Выберите контейнер"
            :filter-option="filterContainer"
            :options="containerOptions"
          />
        </a-form-item>
        <a-form-item label="Описание" name="description">
          <a-input
            v-model:value="formState.description"
            placeholder="Например: Использование крана, Досмотр"
          />
        </a-form-item>
        <a-form-item label="Дата начисления" name="charge_date">
          <a-date-picker
            v-model:value="formState.charge_date"
            format="DD.MM.YYYY"
            style="width: 100%"
          />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Сумма USD" name="amount_usd">
              <a-input-number
                v-model:value="formState.amount_usd"
                :min="0.01"
                :precision="2"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Сумма UZS" name="amount_uzs">
              <a-input-number
                v-model:value="formState.amount_uzs"
                :min="1"
                :precision="0"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import type { FormInstance, TableProps } from 'ant-design-vue';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue';
import {
  additionalChargesService,
  type AdditionalCharge,
  type AdditionalChargeSummary,
} from '../../services/additionalChargesService';
import { http } from '../../utils/httpClient';

interface Props {
  companySlug?: string;
  isAdmin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isAdmin: false,
});

const charges = ref<AdditionalCharge[]>([]);
const loading = ref(false);
const searchText = ref('');
const dateRange = ref<[Dayjs, Dayjs] | null>(null);
const summary = ref<AdditionalChargeSummary>({
  total_charges: 0,
  total_usd: '0',
  total_uzs: '0',
});

// Modal state
const modalVisible = ref(false);
const saving = ref(false);
const editingCharge = ref<AdditionalCharge | null>(null);
const formRef = ref<FormInstance>();

interface FormState {
  container_entry: number | null;
  description: string;
  amount_usd: number | null;
  amount_uzs: number | null;
  charge_date: Dayjs | null;
}

const formState = reactive<FormState>({
  container_entry: null,
  description: '',
  amount_usd: null,
  amount_uzs: null,
  charge_date: dayjs(),
});

const formRules = {
  container_entry: [{ required: true, message: 'Выберите контейнер' }],
  description: [{ required: true, message: 'Введите описание' }],
  amount_usd: [{ required: true, message: 'Введите сумму USD' }],
  amount_uzs: [{ required: true, message: 'Введите сумму UZS' }],
  charge_date: [{ required: true, message: 'Выберите дату' }],
};

// Container options for dropdown
const containerOptions = ref<{ label: string; value: number }[]>([]);

const columns: TableProps['columns'] = [
  {
    title: 'Дата',
    key: 'charge_date',
    width: 100,
  },
  {
    title: 'Контейнер',
    key: 'container',
    width: 140,
  },
  {
    title: 'Описание',
    dataIndex: 'description',
    key: 'description',
    width: 200,
  },
  {
    title: 'Сумма USD',
    key: 'amount_usd',
    width: 120,
    align: 'right',
  },
  {
    title: 'Сумма UZS',
    key: 'amount_uzs',
    width: 150,
    align: 'right',
  },
  {
    title: '',
    key: 'actions',
    width: 80,
    align: 'center',
  },
];

// Debounce search
let searchTimeout: ReturnType<typeof setTimeout> | null = null;
watch(searchText, () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(fetchCharges, 400);
});

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('ru-RU');
};

const formatCurrency = (value: string, currency: 'USD' | 'UZS'): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  if (currency === 'USD') {
    return `$${num.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}`;
  }
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0 })} сум`;
};

const formatUzs = (value: string): string => {
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 0 })} сум`;
};

const filterContainer = (input: string, option: { label: string }) => {
  return option.label.toLowerCase().includes(input.toLowerCase());
};

const fetchCharges = async () => {
  loading.value = true;
  try {
    const params: { date_from?: string; date_to?: string; search?: string } = {};

    if (dateRange.value && dateRange.value[0] && dateRange.value[1]) {
      params.date_from = dateRange.value[0].format('YYYY-MM-DD');
      params.date_to = dateRange.value[1].format('YYYY-MM-DD');
    }

    if (searchText.value.trim()) {
      params.search = searchText.value.trim();
    }

    let response;
    if (props.companySlug) {
      response = await additionalChargesService.getCompanyCharges(props.companySlug, params);
    } else {
      response = await additionalChargesService.getCustomerCharges(params);
    }

    charges.value = response.data;
    summary.value = response.summary;
  } catch (error) {
    console.error('Error fetching charges:', error);
    message.error('Не удалось загрузить начисления');
  } finally {
    loading.value = false;
  }
};

const fetchContainers = async () => {
  if (!props.isAdmin) return;

  try {
    // Fetch active containers for the dropdown
    const url = props.companySlug
      ? `/auth/companies/${props.companySlug}/containers/?status=active&page_size=500`
      : '/terminal/entries/?status=active&page_size=500';

    const response = await http.get<{ results: Array<{ id: number; container_number: string }> }>(url);

    containerOptions.value = response.results.map((c: { id: number; container_number: string }) => ({
      label: c.container_number,
      value: c.id,
    }));
  } catch (error) {
    console.error('Error fetching containers:', error);
  }
};

const openAddModal = () => {
  editingCharge.value = null;
  formState.container_entry = null;
  formState.description = '';
  formState.amount_usd = null;
  formState.amount_uzs = null;
  formState.charge_date = dayjs();
  modalVisible.value = true;
  fetchContainers();
};

const openEditModal = (charge: AdditionalCharge) => {
  editingCharge.value = charge;
  formState.container_entry = charge.container_entry;
  formState.description = charge.description;
  formState.amount_usd = parseFloat(charge.amount_usd);
  formState.amount_uzs = parseFloat(charge.amount_uzs);
  formState.charge_date = dayjs(charge.charge_date);
  modalVisible.value = true;
};

const closeModal = () => {
  modalVisible.value = false;
  editingCharge.value = null;
  formRef.value?.resetFields();
};

const handleSave = async () => {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  saving.value = true;
  try {
    const data = {
      container_entry: formState.container_entry!,
      description: formState.description,
      amount_usd: formState.amount_usd!,
      amount_uzs: formState.amount_uzs!,
      charge_date: formState.charge_date!.format('YYYY-MM-DD'),
    };

    if (editingCharge.value) {
      await additionalChargesService.update(editingCharge.value.id, data);
      message.success('Начисление обновлено');
    } else {
      await additionalChargesService.create(data);
      message.success('Начисление добавлено');
    }

    closeModal();
    fetchCharges();
  } catch (error) {
    console.error('Error saving charge:', error);
    message.error('Не удалось сохранить начисление');
  } finally {
    saving.value = false;
  }
};

const deleteCharge = async (id: number) => {
  try {
    await additionalChargesService.delete(id);
    message.success('Начисление удалено');
    fetchCharges();
  } catch (error) {
    console.error('Error deleting charge:', error);
    message.error('Не удалось удалить начисление');
  }
};

onMounted(() => {
  fetchCharges();
});

// Expose method for parent to trigger charge creation
defineExpose({
  openAddModalForContainer: (containerId: number, containerNumber: string) => {
    editingCharge.value = null;
    formState.container_entry = containerId;
    formState.description = '';
    formState.amount_usd = null;
    formState.amount_uzs = null;
    formState.charge_date = dayjs();
    containerOptions.value = [{ label: containerNumber, value: containerId }];
    modalVisible.value = true;
  },
});
</script>

<style scoped>
.additional-charges {
  padding: 8px 0;
}

.header-actions {
  margin-bottom: 16px;
}

.amount-usd {
  font-weight: 600;
  color: #52c41a;
}

.amount-uzs {
  font-weight: 500;
  color: #722ed1;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/billing/AdditionalCharges.vue
git commit -m "feat(frontend): add AdditionalCharges component"
```

---

## Task 7: Integrate into CurrentCosts.vue

**Files:**
- Modify: `frontend/src/components/billing/CurrentCosts.vue`

**Step 1: Import and add AdditionalCharges component**

Add import at the top of `<script setup>`:

```typescript
import AdditionalCharges from './AdditionalCharges.vue';
```

**Step 2: Add ref for AdditionalCharges**

Add after other refs:

```typescript
const additionalChargesRef = ref<InstanceType<typeof AdditionalCharges>>();
```

**Step 3: Add isAdmin computed**

```typescript
const isAdmin = computed(() => !!props.companySlug);
```

**Step 4: Add double-click handler**

Add new function:

```typescript
const handleRowDoubleClick = (record: StorageCostItem) => {
  if (isAdmin.value && additionalChargesRef.value) {
    additionalChargesRef.value.openAddModalForContainer(
      record.container_entry_id,
      record.container_number
    );
  }
};
```

**Step 5: Update table to use customRow**

Update the `<a-table>` to add double-click:

```vue
<a-table
  ...existing props...
  :custom-row="(record: StorageCostItem) => ({
    onDblclick: () => handleRowDoubleClick(record),
    style: isAdmin ? 'cursor: pointer;' : '',
  })"
>
```

**Step 6: Add AdditionalCharges section in template**

After the existing `<a-table>`, add:

```vue
<!-- Additional Charges Section -->
<a-divider style="margin: 24px 0;">Дополнительные начисления</a-divider>

<AdditionalCharges
  ref="additionalChargesRef"
  :company-slug="companySlug"
  :is-admin="isAdmin"
/>
```

**Step 7: Commit**

```bash
git add frontend/src/components/billing/CurrentCosts.vue
git commit -m "feat(frontend): integrate AdditionalCharges into CurrentCosts"
```

---

## Task 8: Add Company Additional Charges Endpoint (Admin)

**Files:**
- Modify: `backend/apps/accounts/company_views.py`

**Step 1: Add additional charges endpoint to CompanyViewSet**

Add new action method:

```python
from apps.billing.models import AdditionalCharge
from apps.billing.serializers import AdditionalChargeSerializer

# Inside CompanyViewSet class:

@action(detail=True, methods=["get"], url_path="additional-charges")
def additional_charges(self, request, slug=None):
    """Get additional charges for a company's containers."""
    company = self.get_object()

    queryset = AdditionalCharge.objects.filter(
        container_entry__company=company
    ).select_related(
        "container_entry__container",
        "container_entry__company",
        "created_by",
    ).order_by("-charge_date", "-created_at")

    # Filter by date range
    date_from = request.query_params.get("date_from")
    if date_from:
        queryset = queryset.filter(charge_date__gte=date_from)

    date_to = request.query_params.get("date_to")
    if date_to:
        queryset = queryset.filter(charge_date__lte=date_to)

    # Search by container number
    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            container_entry__container__container_number__icontains=search
        )

    # Calculate summary
    from django.db.models import Sum
    totals = queryset.aggregate(
        total_usd=Sum("amount_usd"),
        total_uzs=Sum("amount_uzs"),
    )

    serializer = AdditionalChargeSerializer(queryset, many=True)

    return Response({
        "success": True,
        "data": serializer.data,
        "summary": {
            "total_charges": queryset.count(),
            "total_usd": str(totals["total_usd"] or 0),
            "total_uzs": str(totals["total_uzs"] or 0),
        },
    })
```

**Step 2: Commit**

```bash
git add backend/apps/accounts/company_views.py
git commit -m "feat(accounts): add company additional charges endpoint"
```

---

## Task 9: Test the Implementation

**Step 1: Run backend tests**

```bash
cd backend && pytest apps/billing/ -v
```

**Step 2: Test API manually**

```bash
# Create a charge (as admin)
curl -X POST http://localhost:8008/api/billing/additional-charges/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "container_entry": 1,
    "description": "Crane usage",
    "amount_usd": "25.00",
    "amount_uzs": "300000",
    "charge_date": "2026-01-20"
  }'

# List charges (as customer)
curl http://localhost:8008/api/customer/additional-charges/ \
  -H "Authorization: Bearer <customer_token>"
```

**Step 3: Test frontend**

1. Start the frontend: `cd frontend && npm run dev`
2. Navigate to Billing page
3. Verify Additional Charges section appears below storage costs
4. Test adding a charge (admin only)
5. Test double-click on container row to open charge modal

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found during testing"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | AdditionalCharge model | `models.py`, migration |
| 2 | Serializers | `serializers.py` |
| 3 | API views | `views.py` |
| 4 | URL routing | `urls.py` |
| 5 | Frontend service | `additionalChargesService.ts` |
| 6 | AdditionalCharges component | `AdditionalCharges.vue` |
| 7 | Integration into CurrentCosts | `CurrentCosts.vue` |
| 8 | Company endpoint (admin) | `company_views.py` |
| 9 | Testing | Manual tests |

**Total estimated time:** 2-3 hours
