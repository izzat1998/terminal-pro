<template>
  <div class="login-page">
    <!-- Left Panel: Branding -->
    <div class="branding-panel">
      <div class="branding-content">
        <div class="branding-logo">
          <div class="logo-mark">
            <ContainerOutlined />
          </div>
          <span class="logo-text">MTT Terminal</span>
        </div>

        <div class="branding-hero">
          <h1>Система управления контейнерным терминалом</h1>
          <p>Комплексное решение для автоматизации терминальных операций, учёта контейнеров и транспортных средств</p>
        </div>

        <div class="branding-features">
          <div class="feature-item">
            <CheckCircleOutlined />
            <span>Учёт въезда и выезда контейнеров</span>
          </div>
          <div class="feature-item">
            <CheckCircleOutlined />
            <span>Управление транспортными средствами</span>
          </div>
          <div class="feature-item">
            <CheckCircleOutlined />
            <span>Интеграция с Telegram ботом</span>
          </div>
        </div>

        <div class="branding-footer">
          <p>&copy; 2024 MTT Container Terminal. Все права защищены.</p>
        </div>
      </div>

      <!-- Decorative elements -->
      <div class="branding-decoration">
        <div class="decoration-circle decoration-circle-1"></div>
        <div class="decoration-circle decoration-circle-2"></div>
        <div class="decoration-grid"></div>
      </div>
    </div>

    <!-- Right Panel: Login Form -->
    <div class="form-panel">
      <div class="form-wrapper">
        <!-- Mobile logo (hidden on desktop) -->
        <div class="mobile-logo">
          <div class="logo-mark">
            <ContainerOutlined />
          </div>
          <span class="logo-text">MTT</span>
        </div>

        <div class="form-header">
          <h2>Добро пожаловать</h2>
          <p>Войдите в свою учётную запись для продолжения</p>
        </div>

        <a-form
          :model="formState"
          name="login"
          autocomplete="off"
          @finish="onFinish"
          layout="vertical"
          class="login-form"
        >
          <a-form-item
            name="username"
            :rules="[{ required: true, message: 'Введите имя пользователя' }]"
          >
            <a-input
              v-model:value="formState.username"
              size="large"
              placeholder="Имя пользователя"
              class="form-input"
            >
              <template #prefix>
                <UserOutlined class="input-icon" />
              </template>
            </a-input>
          </a-form-item>

          <a-form-item
            name="password"
            :rules="[{ required: true, message: 'Введите пароль' }]"
          >
            <a-input-password
              v-model:value="formState.password"
              size="large"
              placeholder="Пароль"
              class="form-input"
            >
              <template #prefix>
                <LockOutlined class="input-icon" />
              </template>
            </a-input-password>
          </a-form-item>

          <a-form-item class="submit-item">
            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
              block
              size="large"
              class="submit-btn"
            >
              <template #icon>
                <LoginOutlined />
              </template>
              Войти в систему
            </a-button>
          </a-form-item>

          <a-alert
            v-if="error"
            :message="error"
            type="error"
            show-icon
            closable
            @close="error = null"
            class="error-alert"
          />
        </a-form>

        <div class="form-footer">
          <p>Возникли проблемы со входом? <a href="mailto:support@mtt.uz">Свяжитесь с поддержкой</a></p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  ContainerOutlined,
  UserOutlined,
  LockOutlined,
  LoginOutlined,
  CheckCircleOutlined
} from '@ant-design/icons-vue';
import { useAuth } from '../composables/useAuth';

const router = useRouter();
const { login, loading, error: authError, user } = useAuth();

const formState = reactive({
  username: '',
  password: '',
});

const error = ref<string | null>(null);

const onFinish = async () => {
  const success = await login(formState);

  if (success) {
    // Redirect based on user type
    if (user.value?.user_type === 'customer') {
      router.push('/customer');
    } else {
      router.push('/');
    }
  } else {
    error.value = authError.value;
  }
};
</script>

<style scoped>
/* =============================================================================
   CORPORATE LOGIN PAGE - Split Screen Layout
   ============================================================================= */

.login-page {
  display: flex;
  min-height: 100vh;
  background: #f8fafc;
}

/* =============================================================================
   LEFT PANEL - BRANDING
   ============================================================================= */

.branding-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  color: white;
  position: relative;
  overflow: hidden;
}

.branding-content {
  position: relative;
  z-index: 2;
  max-width: 520px;
}

.branding-logo {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 56px;
}

.logo-mark {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 14px;
  font-size: 26px;
  box-shadow: 0 8px 32px rgba(59, 130, 246, 0.4);
}

.branding-logo .logo-text {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: white;
}

.branding-hero {
  margin-bottom: 48px;
}

.branding-hero h1 {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 20px;
  color: white;
  letter-spacing: -0.5px;
}

.branding-hero p {
  font-size: 17px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
}

.branding-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 48px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.85);
}

.feature-item :deep(.anticon) {
  font-size: 20px;
  color: #22c55e;
}

.branding-footer {
  padding-top: 32px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.branding-footer p {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
}

/* Decorative Elements */
.branding-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
}

.decoration-circle-1 {
  width: 600px;
  height: 600px;
  top: -200px;
  right: -200px;
  animation: floatSlow 30s ease-in-out infinite;
}

.decoration-circle-2 {
  width: 400px;
  height: 400px;
  bottom: -100px;
  left: -100px;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, transparent 70%);
  animation: floatSlow 25s ease-in-out infinite reverse;
}

.decoration-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 64px 64px;
}

@keyframes floatSlow {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, 20px) scale(1.05); }
}

/* =============================================================================
   RIGHT PANEL - LOGIN FORM
   ============================================================================= */

.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: #ffffff;
}

.form-wrapper {
  width: 100%;
  max-width: 400px;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.mobile-logo {
  display: none;
}

.form-header {
  margin-bottom: 40px;
  text-align: center;
}

.form-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 10px;
  letter-spacing: -0.5px;
}

.form-header p {
  font-size: 15px;
  color: #64748b;
  margin: 0;
}

/* Form Styling */
.login-form {
  margin-bottom: 32px;
}

.login-form :deep(.ant-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.ant-form-item-label) {
  display: none;
}

/* Style the wrapper (contains prefix icon + input) */
.form-input :deep(.ant-input-affix-wrapper) {
  height: 52px;
  padding: 0 16px;
  border-radius: 12px;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  transition: all 0.2s ease;
}

.form-input :deep(.ant-input-affix-wrapper:hover) {
  border-color: #3b82f6;
}

.form-input :deep(.ant-input-affix-wrapper-focused),
.form-input :deep(.ant-input-affix-wrapper:focus-within) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Inner input should have NO border - wrapper handles it */
.form-input :deep(.ant-input-affix-wrapper .ant-input) {
  height: 100%;
  border: none !important;
  box-shadow: none !important;
  padding: 0;
  font-size: 15px;
  background: transparent;
}

/* Password input specific */
.form-input :deep(.ant-input-password .ant-input) {
  border: none !important;
  box-shadow: none !important;
}

.input-icon {
  color: #94a3b8;
  font-size: 18px;
  margin-right: 4px;
}

.submit-item {
  margin-bottom: 0 !important;
}

.submit-btn {
  height: 52px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  border-radius: 12px !important;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.35) !important;
  transition: all 0.25s ease !important;
}

.submit-btn:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4) !important;
}

.submit-btn:active {
  transform: translateY(0) !important;
}

.submit-btn :deep(.anticon) {
  font-size: 18px;
}

.error-alert {
  margin-top: 20px;
  border-radius: 10px;
}

.form-footer {
  text-align: center;
}

.form-footer p {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.form-footer a {
  color: #3b82f6;
  font-weight: 500;
  text-decoration: none;
  transition: color 0.2s ease;
}

.form-footer a:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

/* =============================================================================
   RESPONSIVE DESIGN
   ============================================================================= */

@media (max-width: 1024px) {
  .branding-panel {
    padding: 40px;
  }

  .branding-hero h1 {
    font-size: 30px;
  }

  .form-panel {
    padding: 40px;
  }
}

@media (max-width: 768px) {
  .login-page {
    flex-direction: column;
  }

  .branding-panel {
    display: none;
  }

  .form-panel {
    min-height: 100vh;
    padding: 24px;
    background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  }

  .mobile-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 40px;
  }

  .mobile-logo .logo-mark {
    width: 44px;
    height: 44px;
    font-size: 22px;
  }

  .mobile-logo .logo-text {
    font-size: 28px;
    font-weight: 700;
    color: #0f172a;
  }

  .form-header {
    margin-bottom: 32px;
  }

  .form-header h2 {
    font-size: 24px;
  }
}

@media (max-width: 480px) {
  .form-panel {
    padding: 20px;
  }

  .form-wrapper {
    max-width: 100%;
  }

  .form-input :deep(.ant-input),
  .form-input :deep(.ant-input-affix-wrapper) {
    height: 48px;
  }

  .submit-btn {
    height: 48px !important;
  }
}
</style>
