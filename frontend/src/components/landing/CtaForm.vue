<script setup lang="ts">
import { ref, reactive } from 'vue';
import type { FormInstance, Rule } from 'ant-design-vue/es/form';

interface FormState {
  name: string;
  company: string;
  email: string;
  phone: string;
}

const formRef = ref<FormInstance | undefined>(undefined);
const loading = ref(false);
const submitted = ref(false);

const formState = reactive<FormState>({
  name: '',
  company: '',
  email: '',
  phone: '',
});

const rules: Record<string, Rule[]> = {
  name: [
    { required: true, message: 'Please enter your name', trigger: 'blur' },
    { min: 2, message: 'Name must be at least 2 characters', trigger: 'blur' },
  ],
  company: [
    { required: true, message: 'Please enter your company name', trigger: 'blur' },
  ],
  email: [
    { required: true, message: 'Please enter your email', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: 'Please enter your phone number', trigger: 'blur' },
  ],
};

const handleSubmit = async () => {
  try {
    await formRef.value?.validate();
    loading.value = true;

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));

    submitted.value = true;
  } catch (error) {
    console.error('Validation failed:', error);
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  submitted.value = false;
  formState.name = '';
  formState.company = '';
  formState.email = '';
  formState.phone = '';
  formRef.value?.resetFields();
};
</script>

<template>
  <div class="cta-form">
    <template v-if="!submitted">
      <h3 class="form-title">Ready to transform your terminal?</h3>
      <p class="form-subtitle">
        Get a personalized demo and see how MTT can optimize your operations.
      </p>

      <a-form
        ref="formRef"
        :model="formState"
        :rules="rules"
        layout="vertical"
        @finish="handleSubmit"
      >
        <a-form-item label="Full Name" name="name">
          <a-input
            v-model:value="formState.name"
            placeholder="John Doe"
            size="large"
          >
            <template #prefix>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </template>
          </a-input>
        </a-form-item>

        <a-form-item label="Company" name="company">
          <a-input
            v-model:value="formState.company"
            placeholder="Your company name"
            size="large"
          >
            <template #prefix>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="7" width="20" height="14" rx="2" />
                <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16" />
              </svg>
            </template>
          </a-input>
        </a-form-item>

        <a-form-item label="Email" name="email">
          <a-input
            v-model:value="formState.email"
            placeholder="john@company.com"
            size="large"
          >
            <template #prefix>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
            </template>
          </a-input>
        </a-form-item>

        <a-form-item label="Phone" name="phone">
          <a-input
            v-model:value="formState.phone"
            placeholder="+998 90 123 45 67"
            size="large"
          >
            <template #prefix>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" />
              </svg>
            </template>
          </a-input>
        </a-form-item>

        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            :loading="loading"
            block
            class="submit-btn"
          >
            Request Demo
          </a-button>
        </a-form-item>
      </a-form>

      <p class="form-note">
        By submitting, you agree to our
        <a href="#">Privacy Policy</a> and <a href="#">Terms of Service</a>.
      </p>
    </template>

    <template v-else>
      <div class="success-message">
        <div class="success-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        </div>
        <h3 class="success-title">Thank you!</h3>
        <p class="success-text">
          We've received your request. Our team will contact you within 24 hours to schedule your personalized demo.
        </p>
        <a-button size="large" @click="resetForm">Submit another request</a-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.cta-form {
  background: white;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}

.form-title {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 8px 0;
  text-align: center;
}

.form-subtitle {
  font-size: 16px;
  color: #6b7280;
  text-align: center;
  margin: 0 0 32px 0;
}

.submit-btn {
  height: 52px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #e94560 0%, #ff6b6b 100%);
  border: none;
  border-radius: 10px;
  margin-top: 8px;
}

.submit-btn:hover {
  background: linear-gradient(135deg, #d63654 0%, #ff5252 100%);
}

.form-note {
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
  margin-top: 8px;
}

.form-note a {
  color: #6b7280;
  text-decoration: underline;
}

.success-message {
  text-align: center;
  padding: 40px 20px;
}

.success-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #16a34a;
}

.success-title {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 12px 0;
}

.success-text {
  font-size: 16px;
  color: #6b7280;
  margin: 0 0 24px 0;
  line-height: 1.6;
}
</style>
