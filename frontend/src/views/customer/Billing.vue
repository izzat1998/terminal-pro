<template>
  <a-card :bordered="false" class="billing-card">
    <template #title>
      <div class="card-title">
        <DollarOutlined style="color: #52c41a; margin-right: 8px;" />
        Биллинг
      </div>
    </template>

    <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
      <a-tab-pane key="current" tab="Текущие расходы">
        <CurrentCosts />
      </a-tab-pane>
      <a-tab-pane key="statements" tab="Ежемесячные счета">
        <MonthlyStatements />
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

const route = useRoute();
const router = useRouter();

const activeTab = ref<string>('current');

onMounted(() => {
  // Check for tab query param
  const tab = route.query.tab as string;
  if (tab === 'statements') {
    activeTab.value = 'statements';
  }
});

const handleTabChange = (key: string) => {
  router.replace({ query: { ...route.query, tab: key === 'current' ? undefined : key } });
};
</script>

<style scoped>
.billing-card {
  border-radius: 2px;
}

.card-title {
  display: flex;
  align-items: center;
}
</style>
