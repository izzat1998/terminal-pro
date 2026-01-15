<script setup lang="ts">
import ruRU from 'ant-design-vue/es/locale/ru_RU';
import { appTheme } from './theme';
</script>

<template>
  <a-config-provider :locale="ruRU" :theme="appTheme">
    <a-app>
      <router-view />
    </a-app>
  </a-config-provider>
</template>
