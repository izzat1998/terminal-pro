<template>
  <a-modal
    v-model:open="visible"
    :title="modalTitle"
    :width="modalWidth"
    :footer="null"
    :destroy-on-close="true"
    class="document-preview-modal"
  >
    <a-tabs v-model:activeKey="activeTab" @change="onTabChange">
      <a-tab-pane key="excel" tab="Детализация Excel" />
      <a-tab-pane key="pdf" tab="Детализация PDF" />
      <a-tab-pane key="act" tab="Счёт-фактура" />
    </a-tabs>

    <!-- Preview area -->
    <div class="preview-container">
      <div v-if="loading" class="preview-loading">
        <a-spin size="large" tip="Загрузка документа..." />
      </div>
      <div v-else-if="errorMessage" class="preview-error">
        <a-result status="error" :title="errorMessage" sub-title="Попробуйте ещё раз">
          <template #extra>
            <a-button type="primary" @click="loadPreview">Повторить</a-button>
          </template>
        </a-result>
      </div>
      <iframe
        v-else-if="previewUrl"
        :src="previewUrl"
        class="preview-iframe"
      />
      <div v-else class="preview-empty">
        <a-empty description="Нажмите на вкладку для предпросмотра" />
      </div>
    </div>

    <!-- Footer -->
    <div class="preview-footer">
      <a-button @click="visible = false">Закрыть</a-button>
      <a-button type="primary" :loading="downloading" @click="downloadFile">
        <template #icon><DownloadOutlined /></template>
        Скачать {{ downloadLabel }}
      </a-button>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { message } from 'ant-design-vue';
import { DownloadOutlined } from '@ant-design/icons-vue';
import { downloadBlob } from '../../utils/download';
import { getStorageItem } from '../../utils/storage';
import { API_BASE_URL } from '../../config/api';

interface StatementRecord {
  id: number;
  year: number;
  month: number;
  month_name: string;
  company_name: string;
}

interface Props {
  open: boolean;
  record: StatementRecord | null;
  billingBaseUrl: string;
  initialTab?: 'excel' | 'pdf' | 'act';
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = withDefaults(defineProps<Props>(), {
  initialTab: 'pdf',
});

const emit = defineEmits<Emits>();

const visible = ref(props.open);
const activeTab = ref<string>(props.initialTab);
const loading = ref(false);
const downloading = ref(false);
const errorMessage = ref<string | null>(null);
const previewUrl = ref<string | null>(null);

// Cache blobs per tab to avoid re-fetching
const blobCache = ref<Record<string, Blob>>({});
const urlCache = ref<Record<string, string>>({});

const modalWidth = 'min(90vw, 1200px)';

const modalTitle = computed(() => {
  if (!props.record) return 'Предпросмотр';
  return `Предпросмотр: ${props.record.month_name} ${props.record.year}`;
});

const downloadLabel = computed(() => {
  const labels: Record<string, string> = {
    excel: '(Excel)',
    pdf: '(PDF)',
    act: '(Счёт-фактура)',
  };
  return labels[activeTab.value] || '';
});

// Map tab → preview endpoint (all render as HTML for instant preview)
const previewEndpointMap: Record<string, string> = {
  excel: 'export/html-preview/',
  pdf: 'export/html-preview/',
  act: 'export/act-html-preview/',
};

// Map tab → download endpoint (native format)
const downloadEndpointMap: Record<string, string> = {
  excel: 'export/excel/',
  pdf: 'export/pdf/',
  act: 'export/act/',
};

function buildUrl(endpoint: string): string {
  if (!props.record) return '';
  return `${API_BASE_URL}${props.billingBaseUrl}/statements/${props.record.year}/${props.record.month}/${endpoint}`;
}

async function fetchBlob(url: string): Promise<Blob> {
  const token = getStorageItem('access_token');
  const response = await fetch(url, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.blob();
}

async function loadPreview(): Promise<void> {
  const tab = activeTab.value;

  // Always clear error/loading before checking cache
  errorMessage.value = null;

  // Return cached URL if available
  if (urlCache.value[tab]) {
    previewUrl.value = urlCache.value[tab];
    return;
  }

  loading.value = true;
  previewUrl.value = null;

  try {
    const endpoint = previewEndpointMap[tab];
    const url = buildUrl(endpoint);

    // Excel & PDF tabs share the same html-preview endpoint — reuse cache
    const cacheKey = (tab === 'excel' || tab === 'pdf') ? 'detail' : tab;
    let blob = blobCache.value[cacheKey];

    if (!blob) {
      blob = await fetchBlob(url);
      blobCache.value[cacheKey] = blob;
    }

    const objectUrl = URL.createObjectURL(blob);
    urlCache.value[tab] = objectUrl;

    // Share the URL between excel and pdf tabs
    if (tab === 'excel' || tab === 'pdf') {
      urlCache.value['excel'] = objectUrl;
      urlCache.value['pdf'] = objectUrl;
    }

    previewUrl.value = objectUrl;
  } catch {
    errorMessage.value = 'Не удалось загрузить документ';
  } finally {
    loading.value = false;
  }
}

async function downloadFile(): Promise<void> {
  if (!props.record) return;

  downloading.value = true;
  try {
    const tab = activeTab.value;
    const endpoint = downloadEndpointMap[tab];
    const url = buildUrl(endpoint);
    const blob = await fetchBlob(url);

    const ext = tab === 'pdf' ? 'pdf' : 'xlsx';
    const prefix = tab === 'act' ? 'sf' : 'statement';
    const filename = `${prefix}_${props.record.year}_${String(props.record.month).padStart(2, '0')}.${ext}`;

    downloadBlob(blob, filename);
    message.success('Файл скачан');
  } catch {
    message.error('Не удалось скачать файл');
  } finally {
    downloading.value = false;
  }
}

function onTabChange(): void {
  loadPreview();
}

function cleanupUrls(): void {
  for (const url of Object.values(urlCache.value)) {
    URL.revokeObjectURL(url);
  }
  urlCache.value = {};
  blobCache.value = {};
  previewUrl.value = null;
}

// Sync open state with parent
watch(
  () => props.open,
  (val) => {
    visible.value = val;
    if (val && props.record) {
      activeTab.value = props.initialTab;
      cleanupUrls();
      loadPreview();
    }
  },
);

watch(visible, (val) => {
  if (!val) {
    emit('update:open', false);
    cleanupUrls();
  }
});

onBeforeUnmount(() => {
  cleanupUrls();
});
</script>

<style scoped>
.preview-container {
  position: relative;
  min-height: 70vh;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  background: #fafafa;
}

.preview-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 70vh;
}

.preview-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 70vh;
}

.preview-iframe {
  width: 100%;
  height: 70vh;
  border: none;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 70vh;
}

.preview-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
</style>
