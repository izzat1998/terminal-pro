<template>
  <a-card :bordered="false">
    <template #title>
      <div style="display: flex; align-items: center;">
        <SettingOutlined style="margin-right: 8px;" />
        Настройки терминала
      </div>
    </template>

    <a-spin :spinning="loading">
      <a-form
        :model="form"
        layout="vertical"
        @finish="handleSave"
      >
        <!-- Company Info -->
        <a-divider orientation="left">Реквизиты организации</a-divider>

        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item label="Наименование организации" name="company_name">
              <a-input v-model:value="form.company_name" placeholder='ООО "MULTIMODAL TRANS TERMINAL"' />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item label="Телефон" name="phone">
              <a-input v-model:value="form.phone" placeholder="1503388" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="Юридический адрес" name="legal_address">
          <a-textarea v-model:value="form.legal_address" :rows="2" placeholder="Таш.обл., Зангиатинский р-н..." />
        </a-form-item>

        <a-form-item label="Действует на основании" name="basis_document">
          <a-input v-model:value="form.basis_document" placeholder="Устава" />
        </a-form-item>

        <!-- Bank Details -->
        <a-divider orientation="left">Банковские реквизиты</a-divider>

        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item label="Банк" name="bank_name">
              <a-input v-model:value="form.bank_name" placeholder='АКБ "Xamkor Bank"' />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item label="Расчётный счёт" name="bank_account">
              <a-input v-model:value="form.bank_account" placeholder="2020 8000 2002 7354 8001" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :xs="24" :md="8">
            <a-form-item label="МФО" name="mfo">
              <a-input v-model:value="form.mfo" placeholder="00083" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="ИНН" name="inn">
              <a-input v-model:value="form.inn" placeholder="207202576" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="Код плательщика НДС" name="vat_registration_code">
              <a-input v-model:value="form.vat_registration_code" placeholder="327040006645" />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- Tax & Currency -->
        <a-divider orientation="left">Налоги и валюта</a-divider>

        <a-row :gutter="16">
          <a-col :xs="24" :md="8">
            <a-form-item label="Ставка НДС (%)" name="vat_rate">
              <a-input-number
                v-model:value="form.vat_rate"
                :min="0"
                :max="100"
                :precision="2"
                style="width: 100%"
                addon-after="%"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="Курс USD → UZS" name="default_usd_uzs_rate">
              <a-input-number
                v-model:value="form.default_usd_uzs_rate"
                :min="0"
                :precision="2"
                style="width: 100%"
                :formatter="(value: string) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')"
                :parser="(value: string) => value.replace(/\s/g, '')"
                addon-after="сум"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- Signatories -->
        <a-divider orientation="left">Подписанты</a-divider>

        <a-row :gutter="16">
          <a-col :xs="24" :md="8">
            <a-form-item label="Руководитель (ФИО)" name="director_name">
              <a-input v-model:value="form.director_name" placeholder="Талипов Х.Х." />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="Должность руководителя" name="director_title">
              <a-input v-model:value="form.director_title" placeholder="Руководитель" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="Гл. бухгалтер (ФИО)" name="accountant_name">
              <a-input v-model:value="form.accountant_name" placeholder="Иристаева Н.Т." />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- Save Button -->
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="saving" size="large">
            Сохранить
          </a-button>
          <span v-if="lastSaved" style="margin-left: 12px; color: #999; font-size: 13px;">
            Последнее обновление: {{ lastSaved }}
          </span>
        </a-form-item>
      </a-form>
    </a-spin>
  </a-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { SettingOutlined } from '@ant-design/icons-vue';
import { http } from '../utils/httpClient';
import { formatDateTime } from '../utils/dateFormat';

interface TerminalSettingsForm {
  company_name: string;
  legal_address: string;
  phone: string;
  bank_name: string;
  bank_account: string;
  mfo: string;
  inn: string;
  vat_registration_code: string;
  vat_rate: number;
  director_name: string;
  director_title: string;
  accountant_name: string;
  basis_document: string;
  default_usd_uzs_rate: number;
}

const loading = ref(false);
const saving = ref(false);
const lastSaved = ref('');

const form = reactive<TerminalSettingsForm>({
  company_name: '',
  legal_address: '',
  phone: '',
  bank_name: '',
  bank_account: '',
  mfo: '',
  inn: '',
  vat_registration_code: '',
  vat_rate: 12,
  director_name: '',
  director_title: 'Руководитель',
  accountant_name: '',
  basis_document: 'Устава',
  default_usd_uzs_rate: 0,
});

const fetchSettings = async () => {
  loading.value = true;
  try {
    const result = await http.get<{ success: boolean; data: TerminalSettingsForm & { updated_at: string } }>(
      '/billing/terminal-settings/'
    );
    const data = result.data;
    Object.assign(form, {
      company_name: data.company_name || '',
      legal_address: data.legal_address || '',
      phone: data.phone || '',
      bank_name: data.bank_name || '',
      bank_account: data.bank_account || '',
      mfo: data.mfo || '',
      inn: data.inn || '',
      vat_registration_code: data.vat_registration_code || '',
      vat_rate: parseFloat(String(data.vat_rate)) || 12,
      director_name: data.director_name || '',
      director_title: data.director_title || 'Руководитель',
      accountant_name: data.accountant_name || '',
      basis_document: data.basis_document || 'Устава',
      default_usd_uzs_rate: parseFloat(String(data.default_usd_uzs_rate)) || 0,
    });
    if (data.updated_at) {
      lastSaved.value = formatDateTime(data.updated_at) || '';
    }
  } catch {
    message.error('Не удалось загрузить настройки');
  } finally {
    loading.value = false;
  }
};

const handleSave = async () => {
  saving.value = true;
  try {
    const result = await http.put<{ success: boolean; data: TerminalSettingsForm & { updated_at: string } }>(
      '/billing/terminal-settings/',
      { ...form }
    );
    if (result.data?.updated_at) {
      lastSaved.value = formatDateTime(result.data.updated_at) || '';
    }
    message.success('Настройки сохранены');
  } catch {
    message.error('Не удалось сохранить настройки');
  } finally {
    saving.value = false;
  }
};

onMounted(fetchSettings);
</script>
