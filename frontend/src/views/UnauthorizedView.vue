<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

function goBack() {
  router.back();
}
</script>

<template>
  <div class="unauthorized-container">
    <a-result
      status="403"
      title="403"
      sub-title="У вас нет доступа к этой странице."
    >
      <template #extra>
        <a-button type="primary" @click="goBack">Назад</a-button>
      </template>
    </a-result>
  </div>
</template>

<style scoped>
.unauthorized-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f0f2f5;
}
</style>
