/**
 * Utilities for integrating API errors with Ant Design Vue forms
 *
 * Usage:
 * ```vue
 * <script setup>
 * import { ref } from 'vue';
 * import type { FormInstance } from 'ant-design-vue';
 * import { message } from 'ant-design-vue';
 * import { http } from '@/utils/httpClient';
 * import { handleFormError, isApiError } from '@/utils/formErrors';
 *
 * const formRef = ref<FormInstance>();
 *
 * const handleSubmit = async () => {
 *   try {
 *     await http.post('/api/...', formData);
 *     message.success('Успешно!');
 *   } catch (error) {
 *     handleFormError(error, formRef.value, {
 *       // Optional: map backend field names to form field names
 *       fieldMapping: { 'license_plate': 'licensePlate' }
 *     });
 *   }
 * };
 * </script>
 * ```
 */

import { message } from 'ant-design-vue';
import type { FormInstance } from 'ant-design-vue';
import { isApiError } from '../types/api';

// Re-export for convenience
export { ApiError, isApiError } from '../types/api';

// Extend FormInstance to include setFields method (exists at runtime but not in types)
interface ExtendedFormInstance extends FormInstance {
  setFields: (fields: Array<{ name: string; errors: string[] }>) => void;
}

export interface FormErrorOptions {
  /**
   * Map backend field names to form field names
   * Example: { 'license_plate': 'licensePlate' }
   */
  fieldMapping?: Record<string, string>;

  /**
   * Show toast for non-field errors (default: true)
   */
  showToast?: boolean;

  /**
   * Custom toast error message (overrides API message)
   */
  toastMessage?: string;

  /**
   * Fields to ignore when setting form errors
   */
  ignoreFields?: string[];
}

/**
 * Handle API error and display it appropriately:
 * - Field errors → Show on form fields
 * - Non-field/general errors → Show as toast
 *
 * @returns true if field errors were set, false otherwise
 */
export function handleFormError(
  error: unknown,
  formRef: FormInstance | undefined,
  options: FormErrorOptions = {}
): boolean {
  const {
    fieldMapping = {},
    showToast = true,
    toastMessage,
    ignoreFields = [],
  } = options;

  // Handle ApiError with field errors
  if (isApiError(error) && error.hasFieldErrors() && formRef) {
    const fieldErrors = error.fieldErrors!;
    const formFields: Array<{ name: string; errors: string[] }> = [];

    for (const [backendField, errors] of Object.entries(fieldErrors)) {
      // Skip ignored fields and non_field_errors
      if (ignoreFields.includes(backendField)) continue;

      // Map backend field name to form field name
      const formField = fieldMapping[backendField] || backendField;

      // Skip non_field_errors - these go to toast
      if (formField === 'non_field_errors') {
        if (showToast && errors.length > 0) {
          message.error(toastMessage || errors[0]);
        }
        continue;
      }

      formFields.push({
        name: formField,
        errors: errors,
      });
    }

    const firstField = formFields[0];
    if (firstField) {
      // Set errors on form fields (with safety check)
      // Cast to extended type since setFields exists at runtime
      const extendedForm = formRef as ExtendedFormInstance;
      if (typeof extendedForm.setFields === 'function') {
        extendedForm.setFields(formFields);

        // Scroll to first error field
        if (typeof formRef.scrollToField === 'function') {
          formRef.scrollToField(firstField.name, {
            behavior: 'smooth',
            block: 'center',
          });
        }

        return true;
      }
    }
  }

  // For non-field errors or non-ApiError, show toast
  if (showToast) {
    if (toastMessage) {
      message.error(toastMessage);
    } else if (isApiError(error)) {
      // If there are field errors that couldn't be displayed on form,
      // show them in a more descriptive way
      if (error.hasFieldErrors() && !formRef) {
        const detailedMessage = buildDetailedErrorMessage(error);
        message.error(detailedMessage, 6); // Show for 6 seconds for detailed errors
      } else {
        message.error(error.message);
      }
    } else if (error instanceof Error) {
      message.error(error.message);
    } else {
      message.error('Произошла неизвестная ошибка');
    }
  }

  return false;
}

/**
 * Build a detailed error message from field errors for toast display
 * Used when field errors can't be shown on form fields
 */
function buildDetailedErrorMessage(error: import('../types/api').ApiError): string {
  if (!error.fieldErrors) {
    return error.message;
  }

  // If the API already provides a descriptive message, use it
  // (the backend now builds descriptive messages)
  if (error.message && !error.message.includes('Проверьте детали')) {
    return error.message;
  }

  // Fallback: build message from field errors
  const errorParts: string[] = [];
  for (const [field, errors] of Object.entries(error.fieldErrors)) {
    if (field === 'non_field_errors') {
      // Non-field errors go first
      errorParts.unshift(errors[0] || '');
    } else {
      const fieldLabel = getFieldLabel(field);
      const firstError = errors[0] || 'ошибка';
      errorParts.push(`${fieldLabel}: ${firstError}`);
    }
  }

  if (errorParts.length === 0) {
    return error.message;
  }

  if (errorParts.length === 1) {
    return errorParts[0] ?? error.message;
  }

  return errorParts.join('; ');
}

/**
 * Get human-readable label for a field name
 */
function getFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    container_number: 'Номер контейнера',
    container_iso_type: 'Тип контейнера',
    status: 'Статус',
    transport_type: 'Тип транспорта',
    transport_number: 'Номер транспорта',
    entry_time: 'Время въезда',
    exit_date: 'Дата выезда',
    cargo_weight: 'Вес груза',
    cargo_name: 'Наименование груза',
    client_name: 'Имя клиента',
    destination: 'Направление',
    location: 'Местоположение',
    notes: 'Примечания',
    username: 'Имя пользователя',
    password: 'Пароль',
    phone_number: 'Номер телефона',
    email: 'Email',
    first_name: 'Имя',
    last_name: 'Фамилия',
    company: 'Компания',
    company_id: 'Компания',
    plate_number: 'Номер машины',
    operation_type: 'Тип операции',
    license_plate: 'Госномер',
    driver_name: 'Имя водителя',
    container_owner: 'Владелец контейнера',
    container_owner_id: 'Владелец контейнера',
    name: 'Название',
    login: 'Логин',
    file: 'Файл',
    image: 'Изображение',
    photo: 'Фото',
  };

  return labels[field] || field.replace(/_/g, ' ');
}

/**
 * Extract error message from any error type
 */
export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Произошла неизвестная ошибка';
}

