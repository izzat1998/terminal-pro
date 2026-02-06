<template>
  <a-card :bordered="false" class="content-card">
    <template #title>
      <div class="card-title">
        <DollarOutlined style="color: #52c41a; margin-right: 8px;" />
        Биллинг компании
      </div>
    </template>

    <a-spin v-if="!company" />

    <a-tabs v-else v-model:activeKey="activeTab" @change="handleTabChange">
      <a-tab-pane key="current" tab="Текущие расходы">
        <CurrentCosts :company-slug="company.slug" />
      </a-tab-pane>
      <a-tab-pane key="statements" tab="Ежемесячные счета">
        <MonthlyStatements :company-slug="company.slug" />
      </a-tab-pane>
      <a-tab-pane key="on-demand">
        <template #tab>
          Разовые счета
          <a-badge v-if="pendingExitCount > 0" :count="pendingExitCount" :number-style="{ backgroundColor: '#faad14' }" />
        </template>
        <OnDemandInvoices :company-slug="company.slug" @pending-exit-count="pendingExitCount = $event" />
      </a-tab-pane>
    </a-tabs>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { DollarOutlined } from '@ant-design/icons-vue';
import CurrentCosts from '../../components/billing/CurrentCosts.vue';
import MonthlyStatements from '../../components/billing/MonthlyStatements.vue';
import OnDemandInvoices from '../../components/billing/OnDemandInvoices.vue';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

defineProps<{
  company: Company | null;
  loading: boolean;
}>();

const route = useRoute();
const router = useRouter();

const activeTab = ref<string>('current');
const pendingExitCount = ref(0);

onMounted(() => {
  const tab = route.query.tab as string;
  if (tab === 'statements' || tab === 'on-demand') {
    activeTab.value = tab;
  }
});

const handleTabChange = (key: string) => {
  router.replace({ query: { ...route.query, tab: key === 'current' ? undefined : key } });
};
</script>

<style scoped>
.content-card {
  border-radius: 2px;
}

.card-title {
  display: flex;
  align-items: center;
}
</style>
