import { computed, type WritableComputedRef } from 'vue';

/**
 * Composable for handling modal visibility with v-model pattern
 * Eliminates the need to write the same computed getter/setter in every modal component
 *
 * @example
 * ```vue
 * <script setup lang="ts">
 * const props = defineProps<{ open: boolean }>();
 * const emit = defineEmits<{ 'update:open': [value: boolean] }>();
 * const visible = useModalVisibility(props, emit);
 * </script>
 *
 * <template>
 *   <a-modal v-model:open="visible">...</a-modal>
 * </template>
 * ```
 */
export function useModalVisibility<
  P extends { open: boolean },
  E extends (event: 'update:open', value: boolean) => void
>(props: P, emit: E): WritableComputedRef<boolean> {
  return computed({
    get: () => props.open,
    set: (value: boolean) => emit('update:open', value),
  });
}
