<script setup lang="ts">
import ruRU from 'ant-design-vue/es/locale/ru_RU';
</script>

<template>
  <a-config-provider :locale="ruRU">
    <router-view />
  </a-config-provider>
</template>