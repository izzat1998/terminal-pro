<template>
  <a-modal
    v-model:open="visible"
    title="Редактировать менеджера"
    :confirm-loading="loading"
    ok-text="Сохранить"
    cancel-text="Отмена"
    @ok="handleSubmit"
    @cancel="handleCancel"
  >
    <a-form :model="formState" layout="vertical" style="margin-top: 1rem;">
      <a-form-item
        label="Имя"
        name="first_name"
        :rules="[{ required: true, message: 'Введите имя' }]"
      >
        <a-input v-model:value="formState.first_name" placeholder="Введите имя" />
      </a-form-item>

      <a-form-item
        label="Телефон"
        name="phone_number"
        :rules="[{ required: true, message: 'Введите телефон' }]"
      >
        <a-input v-model:value="formState.phone_number" placeholder="+998901234567" />
      </a-form-item>

      <a-form-item label="Новый пароль (оставьте пустым, чтобы не менять)">
        <a-input-password
          v-model:value="formState.password"
          placeholder="Введите новый пароль"
        />
      </a-form-item>

      <a-form-item label="Доступ к боту">
        <a-switch v-model:checked="formState.bot_access" />
      </a-form-item>

      <a-form-item label="Доступ к воротам">
        <a-switch v-model:checked="formState.gate_access" />
      </a-form-item>

      <a-form-item label="Доступ к системе">
        <a-switch v-model:checked="formState.is_active" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue';
import { message } from 'ant-design-vue';
import { http } from '../utils/httpClient';
import { useModalVisibility } from '../composables/useModalVisibility';

interface Props {
  open: boolean;
  managerId?: number;
  firstName?: string;
  phoneNumber?: string;
  botAccess?: boolean;
  gateAccess?: boolean;
  isActive?: boolean;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'success'): void;
}

interface FormState {
  first_name: string;
  phone_number: string;
  password: string;
  bot_access: boolean;
  gate_access: boolean;
  is_active: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = useModalVisibility(props, emit);

const loading = ref(false);

const formState = reactive<FormState>({
  first_name: '',
  phone_number: '',
  password: '',
  bot_access: true,
  gate_access: true,
  is_active: true,
});

const loadFormData = () => {
  if (props.firstName) formState.first_name = props.firstName;
  if (props.phoneNumber) formState.phone_number = props.phoneNumber;
  if (props.botAccess !== undefined) formState.bot_access = props.botAccess;
  if (props.gateAccess !== undefined) formState.gate_access = props.gateAccess;
  if (props.isActive !== undefined) formState.is_active = props.isActive;
  formState.password = ''; // Always reset password field
};

const resetForm = () => {
  formState.first_name = '';
  formState.phone_number = '';
  formState.password = '';
  formState.bot_access = true;
  formState.gate_access = true;
  formState.is_active = true;
};

const handleSubmit = async () => {
  // Validate required fields
  if (!formState.first_name.trim()) {
    message.error('Пожалуйста, введите имя');
    return;
  }

  if (!formState.phone_number.trim()) {
    message.error('Пожалуйста, введите телефон');
    return;
  }

  // Validate phone number format (Uzbekistan format: +998XXXXXXXXX)
  const phoneRegex = /^\+998\d{9}$/;
  if (!phoneRegex.test(formState.phone_number)) {
    message.error('Неверный формат телефона. Используйте формат: +998XXXXXXXXX');
    return;
  }

  if (!props.managerId) {
    message.error('Не указан ID менеджера');
    return;
  }

  loading.value = true;

  try {
    // Prepare data - only include password if it's not empty
    const submitData: any = {
      first_name: formState.first_name,
      phone_number: formState.phone_number,
      bot_access: formState.bot_access,
      gate_access: formState.gate_access,
      is_active: formState.is_active,
    };

    // Only include password if user entered a new one
    if (formState.password.trim()) {
      if (formState.password.length < 8) {
        message.error('Пароль должен содержать минимум 8 символов');
        loading.value = false;
        return;
      }
      submitData.password = formState.password;
    }

    await http.patch(`/auth/managers/${props.managerId}/`, submitData);

    message.success('Менеджер успешно обновлён');
    emit('success');
    visible.value = false;
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Ошибка обновления менеджера');
  } finally {
    loading.value = false;
  }
};

const handleCancel = () => {
  resetForm();
  visible.value = false;
};

// Load form data when modal opens
watch(visible, (newValue) => {
  if (newValue) {
    loadFormData();
  } else {
    resetForm();
  }
});
</script>
